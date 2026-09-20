#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mint_judge.py  --  운영적 난이도 라벨링 + 품질 Q + Cohen's kappa
================================================================
식(3/4) 라우팅 정확도와 식(5) 품질 Q를 채우려면 '실제 LLM 호출'이 필요하다.
이 스크립트는 본인 PC에서 API 키로 실행한다(이 샌드박스는 키가 없어 --mock만 가능).

판단 기준
  · 난이도(difficulty_gold) = 최상위(L3) 답과 '동등 이상'인 가장 싼 계층
      L1 충분 -> simple / L2 충분 -> moderate / 둘 다 부족 -> complex
  · 품질 Q = minT(라우팅) 응답 vs baseline(전량 L3) 응답을 심판이 비교
      Q = (#동등 + #minT우위) / #전체,  Wilson 95% CI
  · 심판은 순서 편향 완화를 위해 A/B를 바꿔 2번 호출해 합의

설치/실행:
  pip install anthropic
  export ANTHROPIC_API_KEY=sk-ant-...
  python mint_judge.py --task label   --in run/queries.jsonl --out run/queries_labeled.jsonl --n 100
  python mint_judge.py --task quality --in run/queries_labeled.jsonl --out run/quality.json --n 100
  python mint_judge.py --task kappa   --judgments run/judgments.jsonl --human run/human.csv
  # 비용/호출수만 추정:  --estimate
  # 오프라인 로직 검증:   --mock
"""
import argparse, json, os, re, math, random, hashlib, time
random.seed(42)

# ===== 계층/모델 (본인 환경에 맞게 수정) =====
TIERS = {"L1": "claude-haiku-4-5-20251001", "L2": "claude-sonnet-4-6", "L3": "claude-opus-4-8"}
ORDER = ["L1", "L2", "L3"]
JUDGE_MODEL = "claude-opus-4-8"      # 강한 심판 권장(자기선호 편향은 한계로 명시)
DIFF_OF = {"L1": "simple", "L2": "moderate", "L3": "complex"}
CACHE_PATH = ".mint_llm_cache.json"

# ===== 복잡도(라우터) — 하니스와 동일 =====
from kiwipiepy import Kiwi
kiwi = Kiwi()
DROP={"JKS","JKC","JKG","JKO","JKB","JKV","JKQ","JX","JC","EP","EF","EC","ETN","ETM","VX","SF","SP","SE","SS","SO","SW","SB"}
STOP={"좀","한번","다시"}; NEG={"안","못","말","않","아니","아니하","못하"}
def nsafe(p):
    if not re.search(r"[가-힣]",p): return " ".join(re.findall(r"[a-z0-9]+",p.lower()))
    out,n=[],False
    for t in kiwi.tokenize(p):
        if t.form in NEG: n=True; continue
        if t.form in STOP or t.tag in DROP: continue
        out.append(t.form)
    if n: out.append("[NEG]")
    return " ".join(out)
def mcount(p): return len([t for t in kiwi.tokenize(p) if t.tag not in {"SF","SP","SE","SS","SO","SW","SB"}]) if re.search(r"[가-힣]",p) else len(re.findall(r"[A-Za-z0-9]+",p))
TECH=["api","시스템","아키텍처","분산","cqrs","엔드포인트","리팩토링","코드","버그","sql","서버","배포","auth","database"]
RSN=["설계","분석","트레이드오프","비교","최적화","증명","설명","왜","원인","design","analyze","optimize","explain"]
def sigmoid(z): return 1/(1+math.exp(-z))
def complexity(p):
    low=nsafe(p).lower()
    z=0.05*mcount(p)+0.8*sum(low.count(k) for k in TECH)+0.5*sum(low.count(k) for k in RSN)-2.0
    return sigmoid(z)
def route(p): s=complexity(p); return "L1" if s<=0.35 else ("L2" if s<=0.65 else "L3")

def wilson(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return ((c-h)/d,(c+h)/d)

# ===== LLM 클라이언트 (실모드/목모드) =====
class Client:
    def __init__(self, mock=False):
        self.mock=mock; self.calls=0
        self.cache={}
        if not mock:
            import anthropic
            self.api=anthropic.Anthropic()  # ANTHROPIC_API_KEY 사용
            if os.path.exists(CACHE_PATH):
                self.cache=json.load(open(CACHE_PATH,encoding="utf-8"))
    def _save(self):
        if not self.mock: json.dump(self.cache,open(CACHE_PATH,"w",encoding="utf-8"))
    def complete(self, model, prompt, max_tokens=600):
        ck=hashlib.sha256(f"{model}|{prompt}".encode()).hexdigest()
        if ck in self.cache: return self.cache[ck]
        self.calls+=1
        if self.mock:
            # 목: 계층이 필요수준 이상이면 '좋은' 답, 아니면 '부실' 답
            tier=next((k for k,v in TIERS.items() if v==model), "L3")
            need=route(prompt.split("질문: ")[-1][:120]) if "질문: " in prompt else "L1"
            ok = ORDER.index(tier)>=ORDER.index(need)
            out=f"[{tier}|{'good' if ok else 'weak'}] " + prompt[:24]
        else:
            for attempt in range(5):
                try:
                    r=self.api.messages.create(model=model,max_tokens=max_tokens,
                        messages=[{"role":"user","content":prompt}])
                    out="".join(b.text for b in r.content if getattr(b,"type","")=="text"); break
                except Exception as e:
                    if attempt==4: raise
                    time.sleep(2**attempt)
        self.cache[ck]=out; self._save(); return out
    def _verdict(self, question, A, B):
        prompt=(f"두 답변 중 질문에 더 적합한 것을 고르세요. 동등하면 tie.\n"
                f"오직 JSON으로만: {{\"winner\":\"A|B|tie\"}}\n\n질문: {question}\n\n[A]\n{A}\n\n[B]\n{B}")
        if self.mock:
            ga = "good" in A; gb = "good" in B
            w = "tie" if ga==gb else ("A" if ga else "B"); self.calls+=1
            return w
        raw=self.complete(JUDGE_MODEL, prompt, max_tokens=50)
        m=re.search(r'"winner"\s*:\s*"(A|B|tie)"', raw)
        return m.group(1) if m else "tie"
    def judge(self, question, ans_a, ans_b):
        """A가 더 좋은지 판정. 순서 편향 완화: A/B swap 2회 합의."""
        v1=self._verdict(question, ans_a, ans_b)
        v2=self._verdict(question, ans_b, ans_a)   # 순서 뒤집기
        v2={"A":"B","B":"A","tie":"tie"}[v2]        # 라벨 원복
        if v1==v2: return v1
        return "tie"                                 # 불일치 = 동등 처리(보수적)

def load(p): return [json.loads(l) for l in open(p,encoding="utf-8") if l.strip()]

# ===== TASK: 운영적 난이도 라벨링 =====
def task_label(a, cli):
    Q=load(a.inp); 
    sub=[q for q in Q if not q.get("difficulty_gold")][:a.n] if a.n else Q
    done={}  # 이어하기
    if os.path.exists(a.out):
        for r in load(a.out): done[r["id"]]=r
    qp="질문: {}"
    out_rows=[]
    for i,q in enumerate(Q):
        if q["id"] in done: out_rows.append(done[q["id"]]); continue
        if q not in sub: out_rows.append(q); continue
        text=q["text"]
        r3=cli.complete(TIERS["L3"], qp.format(text))
        r1=cli.complete(TIERS["L1"], qp.format(text))
        if cli.judge(text, r1, r3) in ("A","tie"):
            gold="L1"
        else:
            r2=cli.complete(TIERS["L2"], qp.format(text))
            gold="L2" if cli.judge(text, r2, r3) in ("A","tie") else "L3"
        q=dict(q); q["difficulty_gold"]=DIFF_OF[gold]; out_rows.append(q)
        with open(a.out,"w",encoding="utf-8") as f:   # 체크포인트
            for r in out_rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
        if (i+1)%10==0: print(f"  labeled {i+1}/{len(Q)}  (calls={cli.calls})", flush=True)
    # 분포
    from collections import Counter
    c=Counter(r.get("difficulty_gold") for r in out_rows if r.get("difficulty_gold"))
    print(f"\ndifficulty_gold 분포: {dict(c)}  -> {a.out}")
    print("이제 하니스를 다시 돌리면 식(3/4) 라우팅 정확도가 채워집니다.")

# ===== TASK: 품질 Q =====
def task_quality(a, cli):
    Q=load(a.inp)
    test=[q for q in Q if q.get("split")=="test"] or Q
    if a.n: test=test[:a.n]
    qp="질문: {}"; judg=[]; eq=win=lose=0
    for i,q in enumerate(test):
        text=q["text"]
        base=cli.complete(TIERS["L3"], qp.format(text))           # baseline=전량 L3
        tier=("L1" if q.get("difficulty_gold")=="simple" else
              "L2" if q.get("difficulty_gold")=="moderate" else
              "L3" if q.get("difficulty_gold")=="complex" else route(text))
        mint=cli.complete(TIERS[tier], qp.format(text))           # minT=라우팅 계층
        v=cli.judge(text, mint, base)                            # minT가 더 좋은가?
        lab={"A":"minT우위","tie":"동등","B":"열위"}[v]
        eq+=(lab=="동등"); win+=(lab=="minT우위"); lose+=(lab=="열위")
        judg.append({"id":q["id"],"tier":tier,"label":lab})
        if (i+1)%10==0: print(f"  judged {i+1}/{len(test)} (calls={cli.calls})", flush=True)
    n=len(test); Q5=(eq+win)/n; lo,hi=wilson(eq+win,n)
    rep={"n":n,"동등":eq,"minT우위":win,"열위":lose,
         "Q":round(Q5,4),"Q_CI":[round(lo,4),round(hi,4)]}
    json.dump(rep,open(a.out,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    with open(os.path.join(os.path.dirname(a.out) or ".","judgments.jsonl"),"w",encoding="utf-8") as f:
        for j in judg: f.write(json.dumps(j,ensure_ascii=False)+"\n")
    print(f"\n식(5) Q = {100*Q5:.1f}%  [{100*lo:.1f}, {100*hi:.1f}]   동등 {eq}·우위 {win}·열위 {lose} / {n}")
    print(f"  -> {a.out}, judgments.jsonl 저장")

# ===== TASK: Cohen's kappa (심판 vs 사람) =====
def task_kappa(a):
    J={r["id"]:r["label"] for r in load(a.judgments)}
    import csv
    H={}
    with open(a.human,encoding="utf-8") as f:
        for row in csv.DictReader(f): H[row["id"]]=row["label"]
    ids=[i for i in J if i in H]; n=len(ids)
    if n==0: print("겹치는 id 없음"); return
    cats=sorted(set(J[i] for i in ids)|set(H[i] for i in ids))
    po=sum(J[i]==H[i] for i in ids)/n
    from collections import Counter
    cj=Counter(J[i] for i in ids); ch=Counter(H[i] for i in ids)
    pe=sum((cj[c]/n)*(ch[c]/n) for c in cats)
    kappa=(po-pe)/(1-pe) if pe!=1 else 1.0
    print(f"Cohen's κ = {kappa:.3f}  (일치 {po:.3f}, n={n})  목표 ≥ 0.6")

def estimate(a):
    Q=load(a.inp); n=a.n or len(Q)
    print(f"[추정] 대상 {n}건")
    print(f"  label  : 생성 ~{n}×(2~3) + 심판 ~{n}×(1~2)×2  ≈ {n*4}~{n*7} 호출")
    print(f"  quality: 생성 ~{n}×2 + 심판 ~{n}×2          ≈ {n*4} 호출")
    print("  → 캐시로 중복 호출은 1회만 과금. --n 으로 표본을 줄여 시작 권장.")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--task",choices=["label","quality","kappa"])
    ap.add_argument("--in",dest="inp",default="run/queries.jsonl")
    ap.add_argument("--out",default="run/queries_labeled.jsonl")
    ap.add_argument("--judgments",default="run/judgments.jsonl")
    ap.add_argument("--human",default="run/human.csv")
    ap.add_argument("--n",type=int,default=100)
    ap.add_argument("--mock",action="store_true")
    ap.add_argument("--estimate",action="store_true")
    a=ap.parse_args()
    if a.estimate: estimate(a); return
    if a.task=="kappa": task_kappa(a); return
    cli=Client(mock=a.mock)
    if a.task=="label": task_label(a,cli)
    elif a.task=="quality": task_quality(a,cli)
    print(f"총 호출(목 포함): {cli.calls}")

if __name__=="__main__":
    main()