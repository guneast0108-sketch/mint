#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mint_collect.py  --  minT 실험 데이터 수집기 (본인 PC에서 실행)
================================================================
HuggingFace에서 한국어 질의/로그/STS를 받아 minT 실험용 jsonl로 정리한다.
이 환경(샌드박스)은 huggingface.co 접속이 막혀 있으므로, --demo 로 파이프라인만
검증하고, 실제 다운로드는 본인 PC/Colab에서 (datasets 설치 후) 실행한다.

설치:
    pip install datasets langdetect kiwipiepy pandas
사용:
    python mint_collect.py --out data --realqa 500 --wildchat 5000   # 실제 수집
    python mint_collect.py --demo                                     # 오프라인 동작 검증

산출:
    data/queries.jsonl   {id, text, lang, domain, source, difficulty_gold(=null), split}
    data/stream.jsonl    {ts, user_hash, text, lang}        # WildChat 한국어 트래픽
    data/klue_sts.jsonl  {sentence1, sentence2, score, equiv}  # P 캘리브레이션용
"""
import argparse, json, hashlib, os, re, random
random.seed(42)

# ---------------- 공통 유틸 ----------------
def is_korean(text: str) -> bool:
    """1차: 한글 음절 비율, 2차: langdetect 폴백."""
    if not text: return False
    hangul = len(re.findall(r"[가-힣]", text))
    nonspace = len(re.findall(r"\S", text))
    if nonspace == 0: return False
    if hangul / nonspace >= 0.30: return True
    try:
        from langdetect import detect
        return detect(text) == "ko"
    except Exception:
        return False

def domain_of(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ["def ", "class ", "import ", "함수", "코드", "버그", "api", "sql", "리팩", "컴파일", "에러", "exception"]):
        return "code"
    if any(k in low for k in ["번역", "translate", "영어로", "한국어로"]):
        return "translate"
    if any(k in low for k in ["설계", "아키텍처", "분산", "시스템", "architecture", "분석", "트레이드오프"]):
        return "design"
    return "general"

def write_jsonl(path: str, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  saved {len(rows):>6} rows -> {path}")

def first_field(row, names):
    for n in names:
        if n in row and isinstance(row[n], str) and row[n].strip():
            return row[n].strip()
    return None

# ---------------- 1. KoAlpaca-RealQA (실제 한국어 질의) ----------------
def collect_realqa(out, n):
    from datasets import load_dataset
    print(f"[1] beomi/KoAlpaca-RealQA  (target {n})")
    ds = load_dataset("beomi/KoAlpaca-RealQA", split="train")
    rows = []
    for i, ex in enumerate(ds):
        q = first_field(ex, ["instruction", "question", "text", "prompt", "input"])
        if not q or not is_korean(q):
            continue
        rows.append({"id": f"realqa-{i}", "text": q, "lang": "ko",
                     "domain": domain_of(q), "source": "KoAlpaca-RealQA",
                     "difficulty_gold": None, "split": "train" if random.random() < 0.7 else "test"})
        if len(rows) >= n: break
    return rows

# ---------------- 2. WildChat 한국어 (실제 트래픽 스트림) ----------------
def collect_wildchat(out, n):
    from datasets import load_dataset
    print(f"[2] allenai/WildChat-4.8M  korean stream (target {n}, streaming)")
    ds = load_dataset("allenai/WildChat-4.8M", split="train", streaming=True)
    stream, got = [], 0
    for ex in ds:
        # WildChat: language, timestamp, hashed_ip, conversation[{role,content}]
        if ex.get("language") and ex["language"] != "Korean":
            continue
        conv = ex.get("conversation") or []
        user_turn = next((t.get("content") for t in conv if t.get("role") == "user"), None)
        if not user_turn or not is_korean(user_turn):
            continue
        stream.append({"ts": str(ex.get("timestamp", "")),
                       "user_hash": ex.get("hashed_ip", ""),
                       "text": user_turn.strip(), "lang": "ko"})
        got += 1
        if got >= n: break
    # 타임스탬프 순 정렬 = 현실적 재생 순서
    stream.sort(key=lambda r: r["ts"])
    return stream

# ---------------- 3. KLUE-STS (P 캘리브레이션) ----------------
def collect_klue_sts(out):
    from datasets import load_dataset
    print("[3] klue/klue / sts  (의미 동등 캘리브레이션)")
    try:
        ds = load_dataset("klue/klue", "sts", split="validation")
    except Exception as e:
        print(f"   klue/klue 실패({e}); mteb/KLUE-STS로 폴백")
        ds = load_dataset("mteb/KLUE-STS", split="validation")
    rows = []
    for ex in ds:
        lab = ex.get("labels", {}) or {}
        score = lab.get("label")
        binary = lab.get("binary-label")
        rows.append({"sentence1": ex["sentence1"], "sentence2": ex["sentence2"],
                     "score": score, "equiv": int(binary) if binary is not None else None})
    return rows

# ---------------- demo (오프라인 동작 검증용 mock) ----------------
def demo():
    print("[demo] mock 데이터로 파이프라인만 검증 (네트워크 미사용)")
    mock_q = ["결제 버그를 고쳐줘", "이 함수 설명해 주세요", "fix the auth bug",
              "분산 시스템 아키텍처를 설계해줘", "1 더하기 1은?"]
    rows = []
    for i, q in enumerate(mock_q):
        rows.append({"id": f"demo-{i}", "text": q, "lang": "ko" if is_korean(q) else "en",
                     "domain": domain_of(q), "source": "demo", "difficulty_gold": None,
                     "split": "train" if random.random() < 0.7 else "test"})
    write_jsonl("data_demo/queries.jsonl", rows)
    stream = [{"ts": f"2025-01-0{i+1}", "user_hash": hashlib.sha256(str(i).encode()).hexdigest()[:8],
               "text": random.choice(mock_q), "lang": "ko"} for i in range(8)]
    write_jsonl("data_demo/stream.jsonl", stream)
    write_jsonl("data_demo/klue_sts.jsonl",
                [{"sentence1": "비용을 줄여줘", "sentence2": "비용 좀 절감해줘", "score": 4.2, "equiv": 1},
                 {"sentence1": "주문 취소해줘", "sentence2": "주문 취소하지 마", "score": 1.0, "equiv": 0}])
    print("  -> data_demo/ 에 queries/stream/klue_sts.jsonl 생성됨 (구조 확인용)")

# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--realqa", type=int, default=500)
    ap.add_argument("--wildchat", type=int, default=5000)
    ap.add_argument("--no-klue", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo(); return
    q = collect_realqa(a.out, a.realqa)
    write_jsonl(os.path.join(a.out, "queries.jsonl"), q)
    s = collect_wildchat(a.out, a.wildchat)
    write_jsonl(os.path.join(a.out, "stream.jsonl"), s)
    if not a.no_klue:
        write_jsonl(os.path.join(a.out, "klue_sts.jsonl"), collect_klue_sts(a.out))
    print("\n완료. 다음 단계: 통제 증강(동등/hard-negative) + 난이도 라벨 -> 실험 하니스")

if __name__ == "__main__":
    main()