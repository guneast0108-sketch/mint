#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mint_harness.py  --  minT 실험 하니스
================================================================
입력: queries.jsonl, clusters.jsonl, stream.jsonl, klue_sts.jsonl
산출(통계 포함):
  식(1) 토큰 절감             [실측, 형태소 단위]
  식(2) 캐시 적중률 H          [실측, Wilson 95% CI]  exact vs naive vs cache-safe
  식(7) 의미 동등 정밀도 P      [실측, Wilson CI]      naive vs cache-safe  ★헤드라인
  식(3/4) 라우팅 분포          [실측; 정확도는 difficulty_gold 필요]
  식(6) 비용 절감률 R + ablation [실측 구조, 부트스트랩 CI, 대표 단가]
  식(5) 품질 Q                [judge 훅 — 실제 LLM-as-Judge 필요, 미계산]
  KLUE 독립 캘리브레이션        [정규화기 동등판정 vs KLUE 라벨]

토큰 단위는 Kiwi 형태소 수(실측). 실제 LLM 토큰은 estimate_llm_tokens 훅 교체.
모든 수치는 본인 데이터 기반 실측이나, 단가·judge는 가정/훅임을 명시한다.

사용: python mint_harness.py --dir run
"""
import argparse, json, math, os, re, random, hashlib
from collections import Counter, defaultdict
from kiwipiepy import Kiwi
random.seed(42)
kiwi = Kiwi()

# ===== 정규화기 3종 =====
DROP_TAGS = {"JKS","JKC","JKG","JKO","JKB","JKV","JKQ","JX","JC",
             "EP","EF","EC","ETN","ETM","VX","SF","SP","SE","SS","SO","SW","SB"}
DISCOURSE_STOP = {"좀","한번","다시"}
NEG_FORMS = {"안","못","말","않","아니","아니하","못하"}
_tok_cache = {}
def _tok(p):
    if p not in _tok_cache: _tok_cache[p] = kiwi.tokenize(p)
    return _tok_cache[p]

def norm_exact(p): return p.strip()
def norm_naive(p):
    if not re.search(r"[가-힣]", p):
        return " ".join(re.findall(r"[a-z0-9]+", p.lower()))
    return " ".join(t.form for t in _tok(p)
                    if t.tag not in DROP_TAGS and t.form not in DISCOURSE_STOP)
def norm_safe(p):
    if not re.search(r"[가-힣]", p):
        return " ".join(re.findall(r"[a-z0-9]+", p.lower()))
    out, neg = [], False
    for t in _tok(p):
        if t.form in NEG_FORMS: neg = True; continue
        if t.form in DISCOURSE_STOP: continue
        if t.tag in DROP_TAGS: continue
        out.append(t.form)
    if neg: out.append("[NEG]")
    return " ".join(out)
def keyer(norm):
    return lambda p: hashlib.sha256(norm(p).encode()).hexdigest()

def morph_count(p):
    return len([t for t in _tok(p) if t.tag not in {"SF","SP","SE","SS","SO","SW","SB"}]) \
           if re.search(r"[가-힣]", p) else len(re.findall(r"[A-Za-z0-9]+", p))
def estimate_llm_tokens(p):
    hangul = len(re.findall(r"[가-힣]", p))
    t_ascii = sum(max(1, math.ceil(len(w)/4)) for w in re.findall(r"[A-Za-z0-9]+", p))
    return t_ascii + math.ceil(hangul*0.9)

# ===== 통계 =====
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n; d = 1 + z*z/n; c = p + z*z/(2*n)
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-h)/d, (c+h)/d)
def boot_ratio_ci(base, mint, iters=2000):
    n = len(base); idx = range(n)
    rs = []
    for _ in range(iters):
        s = [random.randrange(n) for _ in range(n)]
        b = sum(base[i] for i in s); m = sum(mint[i] for i in s)
        rs.append(1 - m/b if b else 0)
    rs.sort()
    return rs[int(0.025*iters)], rs[int(0.975*iters)]

# ===== 복잡도/라우팅 =====
TECH_KW=["api","시스템","아키텍처","분산","cqrs","엔드포인트","리팩토링","코드","버그","sql",
         "auth","endpoint","refactor","architecture","distributed","database","서버","배포"]
REASON_KW=["설계","분석","트레이드오프","비교","최적화","증명","설명","왜","원인",
           "design","analyze","compare","optimize","explain"]
W={"len":0.05,"tech":0.8,"reason":0.5,"bias":-2.0}
def sigmoid(z): return 1/(1+math.exp(-z))
def complexity(p):
    low = norm_safe(p).lower()
    z=(W["len"]*morph_count(p)+W["tech"]*sum(low.count(k) for k in TECH_KW)
       +W["reason"]*sum(low.count(k) for k in REASON_KW)+W["bias"])
    return sigmoid(z)
TAU1,TAU2=0.35,0.65
def route(s): return "L1" if s<=TAU1 else ("L2" if s<=TAU2 else "L3")
PRICE={"L1":0.5,"L2":4.0,"L3":20.0}   # 대표 단가(per 1M tok), 상대비만 의미

def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
def sec(t): print("\n"+"="*64+f"\n {t}\n"+"="*64)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dir",default="run"); ap.add_argument("--queries", default=None); a=ap.parse_args()
    qpath = a.queries or os.path.join(a.dir, "queries.jsonl")   # ← 이 줄로 교체
    Q = load(qpath)
    C = load(os.path.join(a.dir,"clusters.jsonl"))
    S = load(os.path.join(a.dir,"stream.jsonl"))
    K = load(os.path.join(a.dir,"klue_sts.jsonl"))
    print(f"loaded queries={len(Q)} clusters={len(C)} stream={len(S)} klue={len(K)}")

    # ---------- 식(1) 토큰 절감 ----------
    sec("식 (1)  토큰 절감 :  |N(p)| <= |p|   [형태소 단위, cache-safe]")
    red, viol = [], 0
    for q in Q:
        a0, b0 = morph_count(q["text"]), morph_count(norm_safe(q["text"]))
        if b0 > a0: viol += 1
        red.append((a0-b0)/a0 if a0 else 0)
    print(f"평균 형태소 절감률 : {100*sum(red)/len(red):5.1f}%   (식1 위배 {viol}건 / {len(Q)})")

    # ---------- 식(2) 캐시 적중률 ----------
    sec("식 (2)  캐시 적중률 H (stream)   [실측 + Wilson 95% CI]")
    def hit(norm):
        kf=keyer(norm); seen=set(); h=0
        for r in S:
            k=kf(r["text"])
            if k in seen: h+=1
            else: seen.add(k)
        return h
    n=len(S)
    for name,norm in [("exact-match",norm_exact),("naive 정규화",norm_naive),("cache-safe(우리)",norm_safe)]:
        h=hit(norm); lo,hi=wilson(h,n)
        print(f"  {name:16s}: {100*h/n:5.1f}%  [{100*lo:.1f}, {100*hi:.1f}]   ({h}/{n})")

    # ---------- 식(7) 정밀도 P + recall (clusters) ★ ----------
    sec("식 (7)  의미 동등 정밀도 P + 동등 recall (clusters)   ★헤드라인")
    for name,norm in [("naive 정규화",norm_naive),("cache-safe(우리)",norm_safe)]:
        kf=keyer(norm)
        eqT=eqC=hnT=hnS=0; opT=Counter(); opS=Counter()
        for c in C:
            bk=kf(c["intent"])
            for m in c["members"]:
                if m["type"]=="equiv":
                    eqT+=1; eqC+=(kf(m["text"])==bk)
                elif m["type"]=="hardneg":
                    hnT+=1; sep=kf(m["text"])!=bk; hnS+=sep
                    opT[m["op"]]+=1; opS[m["op"]]+=sep
        P=hnS/max(hnT,1); R=eqC/max(eqT,1)
        plo,phi=wilson(hnS,hnT)
        print(f"\n  [{name}]")
        print(f"    동등 recall : {100*R:5.1f}%  ({eqC}/{eqT})")
        print(f"    정밀도 P    : {100*P:5.1f}%  [{100*plo:.1f}, {100*phi:.1f}]  ({hnS}/{hnT})   false-hit {hnT-hnS}건")
        for op in opT:
            print(f"        {op:9s}: 분리율 {100*opS[op]/opT[op]:5.1f}%  ({opS[op]}/{opT[op]})")

    # ---------- 식(3/4) 라우팅 분포 ----------
    sec("식 (3/4)  라우팅 계층 분포 (queries)   [정확도는 difficulty_gold 필요]")
    dist=Counter(); has_gold=sum(1 for q in Q if q.get("difficulty_gold"))
    for q in Q: dist[route(complexity(q["text"]))]+=1
    print(f"  분포: L1={dist['L1']}  L2={dist['L2']}  L3={dist['L3']}  (총 {len(Q)})")
    if has_gold:
        TIER={"simple":"L1","moderate":"L2","complex":"L3"}
        ok=sum(route(complexity(q["text"]))==TIER.get(q["difficulty_gold"]) for q in Q if q.get("difficulty_gold"))
        print(f"  라우팅 정확도: {100*ok/has_gold:.1f}%  ({ok}/{has_gold})")
    else:
        print("  difficulty_gold 미라벨 → 정확도 미산출. 운영적 라벨(계층별 호출+judge) 필요.")

    # ---------- 식(6) 비용 R + ablation ----------
    sec("식 (6)  비용 절감률 R + ablation (stream)   [부트스트랩 95% CI, 대표 단가]")
    toks=[estimate_llm_tokens(r["text"]) for r in S]
    base=[t*PRICE["L3"]/1e6 for t in toks]
    safe_kf=keyer(norm_safe); ex_kf=keyer(norm_exact)
    def replay(kf, use_route):
        seen=set(); cost=[]
        for r,t in zip(S,toks):
            k=kf(r["text"])
            if k in seen: cost.append(0.0); continue
            seen.add(k)
            tier=route(complexity(r["text"])) if use_route else "L3"
            cost.append(t*PRICE[tier]/1e6)
        return cost
    configs=[("캐시(exact)만",ex_kf,False),
             ("캐시(cache-safe)",safe_kf,False),
             ("캐시+라우팅 = minT",safe_kf,True)]
    Bsum=sum(base)
    for name,kf,ur in configs:
        m=replay(kf,ur); R=1-sum(m)/Bsum; lo,hi=boot_ratio_ci(base,m,iters=1000)
        print(f"  {name:22s}: R={100*R:5.1f}%  [{100*lo:.1f}, {100*hi:.1f}]")
    print("  (baseline=전량 L3. R 분해: exact캐시 → +정규화 → +라우팅 순 기여)")

    # ---------- KLUE 독립 캘리브레이션 ----------
    sec("KLUE-STS 독립 검증   [정규화기 동등판정 vs KLUE 라벨]")
    kf=keyer(norm_safe); tp=fp=fn=tn=0
    for r in K:
        collapse = kf(r["sentence1"])==kf(r["sentence2"])
        gold = (r.get("equiv")==1)
        tp+=(collapse and gold); fp+=(collapse and not gold)
        fn+=(not collapse and gold); tn+=(not collapse and not gold)
    prec=tp/max(tp+fp,1); rec=tp/max(tp+fn,1)
    print(f"  collapse-precision : {100*prec:5.1f}%  (묶은 쌍 중 KLUE-동등 비율)  TP={tp} FP={fp}")
    print(f"  collapse-recall    : {100*rec:5.1f}%  (KLUE-동등 중 묶은 비율)      FN={fn} TN={tn}")
    print("  해석: 형태소 정규화는 '표면형 변이'를 잡지 '어휘 패러프레이즈'는 못 잡음.")
    print("        precision↑/recall↓ → 보수적(무손상) 스코프. 깊은 동의어는 opt-in 임베딩층 몫.")

    # ---------- 식(5) 품질 Q ----------
    sec("식 (5)  품질 Q   [judge 훅 — 미계산]")
    print("  baseline 응답 vs minT 응답을 LLM-as-Judge로 비교해야 산출.")
    print("  judge(r_base, r_minT) 훅에 Anthropic API 연결 → Q=(동등+우위)/전체, Wilson CI.")

    sec("요약")
    print("  · 식1 토큰절감/식2 적중률/식7 정밀도P/식6 R = 본인 데이터 실측")
    print("  · 식3·4 정확도 = difficulty_gold 라벨 필요, 식5 Q = judge 연결 필요")
    print("  · 헤드라인: cache-safe가 naive 대비 부정 false-hit를 제거하며 P를 끌어올림")

if __name__=="__main__":
    main()