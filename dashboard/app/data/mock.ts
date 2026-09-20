export const company = {
  name: "보쿠메디",
  teamSize: 12,
  period: "2026년 5월",
};

export const metrics = {
  savedKrw: 2143000,
  savedChange: -47,
  totalCalls: 147820,
  avgPerMember: 12318,
  savingsRate: 53,
  savingsBreakdown: { caching: 31, routing: 14, compression: 8 },
  qualityScore: 94,
  qualityBaseline: 92,
};

export const teamMembers = [
  { name: "이서연", role: "Backend", calls: 38420, costKrw: 1200000, savedKrw: 720000, quality: 96 },
  { name: "최민지", role: "ML",      calls: 27180, costKrw: 980000,  savedKrw: 510000, quality: 93 },
  { name: "한지호", role: "Frontend",calls: 19650, costKrw: 620000,  savedKrw: 340000, quality: 95 },
  { name: "정유나", role: "PM",       calls: 14210, costKrw: 410000,  savedKrw: 280000, quality: 92 },
  { name: "강도훈", role: "Backend", calls: 12800, costKrw: 380000,  savedKrw: 190000, quality: 94 },
];

export const qualityReport = {
  totalComparisons: 1847,
  equivalent: { count: 1699, pct: 92 },
  mintWins:   { count: 92,   pct: 5  },
  regression: { count: 56,   pct: 3  },
  modules: [
    { name: "Caching",     total: 628, equivalent: 100, mintWin: 0, regression: 0 },
    { name: "Routing",     total: 782, equivalent: 95,  mintWin: 3, regression: 2 },
    { name: "Compression", total: 437, equivalent: 91,  mintWin: 6, regression: 3 },
  ],
  dailyScores: [
    { label: "5/1 월", score: 93 },
    { label: "5/2 화", score: 94 },
    { label: "5/3 수", score: 92 },
    { label: "5/4 목", score: 95 },
    { label: "5/5 금", score: 94 },
    { label: "5/6 토", score: 96 },
    { label: "5/7 일", score: 94 },
  ],
  sampleComparison: {
    query: "이 결제 모듈의 코드를 분석하고 취약점을 찾아줘",
    baselineText: "\"코드를 검토했습니다. 전반적인 구조는 양호하며, 입력값 검증 로직을 추가하면 좋겠습니다. 보안 관련 모범 사례를 참고하세요...\"",
    baselineSub: "핵심 취약점 미탐지, 구체적 위치·원인 누락",
    mintText: "\"SQL Injection (payment.py:142) — 사용자 입력을 query에 직접 결합. 결제 금액 미검증 (checkout.py:87) — 클라이언트 값 신뢰. CSRF 토큰 미적용 (api/payment.py:23) — POST 엔드포인트 무방비...\"",
    mintSub: "취약점 3건 파일·라인 정확 지목 + 수정 방향 제시",
    verdict: "B 우위 — Compression이 12,840 토큰 코드 컨텍스트를 3,210 토큰으로 압축하는 과정에서 보안 관련 패턴을 노이즈 없이 집중 추출. \"Lost in the Middle\" 억제로 파일 중반부 취약점까지 정확히 탐지한 대표 사례.",
  },
  recommendations: [
    "Compression 활성 범위 확장 — 현재 RAG 전용 → 요약 task 추가 시 +12% 절감 예상",
    "Routing 신뢰도 임계값 0.80 → 0.75 — +8% 절감 (품질 영향 1pt 이내)",
    "회귀 56건 분석 결과 — 모두 코드 디버깅 task에서 발생 → 해당 task만 Routing 자동 OFF 권장",
  ],
};
