"use client";

import Link from "next/link";
import { ShieldCheck, TrendingUp, TrendingDown, Minus, ArrowUpRight, Calendar } from "lucide-react";
import { qualityReport, company } from "@/app/data/mock";

const { equivalent, mintWins, regression, totalComparisons, modules, dailyScores, sampleComparison, recommendations } = qualityReport;

export default function QualityPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header — 메인 대시보드와 동일 */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <Link href="/dashboard" className="text-emerald-700 font-medium hover:opacity-80">🌿 mint</Link>
            <span className="text-gray-300">|</span>
            <span className="text-gray-500">{company.name}</span>
            <span className="text-gray-300">/</span>
            <span className="text-gray-500">품질 검증 리포트</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <Calendar size={12} />
            <span>2026.05.01 — 5.07</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">

        {/* Alert banner */}
        <div className="bg-emerald-50 border border-emerald-100 rounded-lg px-5 py-4 flex items-start gap-3">
          <ShieldCheck size={17} className="text-emerald-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-emerald-800">
              검증 통과 — Shadow Mode + LLM-Judge {totalComparisons.toLocaleString()}건 비교
            </p>
            <p className="text-xs text-emerald-600 mt-0.5">
              mint 적용군이 미적용군과 97% 동등 이상 (동등 {equivalent.pct}% + mint 우위 {mintWins.pct}%)
            </p>
          </div>
        </div>

        {/* Verdict cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white border border-gray-200 rounded-lg px-5 py-4">
            <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-2">
              <Minus size={12} />
              <span>동등 (Tie)</span>
            </div>
            <div className="text-4xl font-medium text-gray-900 mb-1">{equivalent.pct}%</div>
            <div className="text-xs text-gray-400">{equivalent.count.toLocaleString()} / {totalComparisons.toLocaleString()}건</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg px-5 py-4">
            <div className="flex items-center gap-1.5 text-xs text-indigo-400 mb-2">
              <TrendingUp size={12} />
              <span>mint 우위</span>
            </div>
            <div className="text-4xl font-medium text-[#7F77DD] mb-1">{mintWins.pct}%</div>
            <div className="text-xs text-gray-400">{mintWins.count}건 · denoising 효과</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg px-5 py-4">
            <div className="flex items-center gap-1.5 text-xs text-amber-500 mb-2">
              <TrendingDown size={12} />
              <span>기준 우위 (회귀)</span>
            </div>
            <div className="text-4xl font-medium text-[#EF9F27] mb-1">{regression.pct}%</div>
            <div className="text-xs text-gray-400">{regression.count}건 · 자동 재시도 처리</div>
          </div>
        </div>

        {/* Module quality */}
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-medium text-gray-700">최적화 모듈별 품질 영향</h2>
            <div className="flex items-center gap-4">
              {[
                { label: "동등", color: "bg-[#1D9E75]" },
                { label: "mint 우위", color: "bg-[#7F77DD]" },
                { label: "회귀", color: "bg-[#EF9F27]" },
              ].map(({ label, color }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <div className={`w-2.5 h-2.5 rounded-sm ${color}`} />
                  <span className="text-xs text-gray-400">{label}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-5">
            {modules.map((m, i) => (
              <div key={m.name}>
                <div className="flex items-end justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-gray-300">{["①", "②", "③"][i]}</span>
                      <span className="text-sm font-medium text-gray-800">{m.name}</span>
                    </div>
                    <span className="text-xs text-gray-400 ml-4">{m.total.toLocaleString()}건 적용</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {m.name === "Caching"
                      ? <span className="flex items-center gap-1">동등 100% (lossless) <span className="text-emerald-500">↻</span></span>
                      : `동등 ${m.equivalent} · +${m.mintWin} · 회귀 ${m.regression}`
                    }
                  </span>
                </div>
                <div className="flex h-2.5 rounded-sm overflow-hidden bg-gray-100">
                  <div className="bg-[#1D9E75]" style={{ width: `${m.equivalent}%` }} />
                  {m.mintWin > 0 && <div className="bg-[#7F77DD]" style={{ width: `${m.mintWin}%` }} />}
                  {m.regression > 0 && <div className="bg-[#EF9F27]" style={{ width: `${m.regression}%` }} />}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Daily bar chart */}
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-medium text-gray-700 mb-4">일별 품질 점수 (LLM-Judge 평균)</h2>
          <ScoreBarChart data={dailyScores} />
        </div>

        {/* Sample comparison */}
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-medium text-gray-700 mb-3">샘플 비교 — mint 우위 사례 #428</h2>
          <div className="bg-gray-50 border border-gray-100 rounded-md px-4 py-3 mb-3">
            <p className="text-xs text-gray-400 mb-1">사용자 쿼리 · 결제 모듈 코드 리뷰</p>
            <p className="text-sm text-gray-800">"{sampleComparison.query}"</p>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="bg-gray-50 border border-gray-100 rounded-md p-4">
              <p className="text-xs text-gray-400 mb-2">A. 미적용 (baseline)</p>
              <p className="text-sm text-gray-600 leading-relaxed">{sampleComparison.baselineText}</p>
              <p className="text-xs text-gray-400 mt-2">— {sampleComparison.baselineSub}</p>
            </div>
            <div className="bg-emerald-50 border border-emerald-100 rounded-md p-4">
              <div className="flex items-center gap-1 mb-2">
                <p className="text-xs text-emerald-700">B. mint 적용</p>
                <span className="text-emerald-600 text-xs">✓</span>
              </div>
              <p className="text-sm text-emerald-900 leading-relaxed">{sampleComparison.mintText}</p>
              <p className="text-xs text-emerald-600 mt-2">— {sampleComparison.mintSub}</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">
            <span className="font-medium text-gray-700">Judge 판정: </span>
            {sampleComparison.verdict}
          </p>
        </div>

        {/* Recommendations */}
        <div className="bg-amber-50 border border-amber-100 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-3">
            <span>💡</span>
            <h2 className="text-sm font-medium text-gray-700">자동 추천 (다음 주 적용 시 예상 효과)</h2>
          </div>
          <ul className="space-y-2 mb-4">
            {recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="text-gray-300 shrink-0 mt-0.5">•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
          <button className="flex items-center gap-1.5 px-4 py-2 bg-white border border-gray-200 hover:bg-gray-50 rounded-md text-sm text-gray-700 transition-colors">
            한 번에 적용
            <ArrowUpRight size={13} />
          </button>
        </div>

      </main>
    </div>
  );
}

function ScoreBarChart({ data }: { data: { label: string; score: number }[] }) {
  const W = 620;
  const H = 160;
  const padTop = 22;
  const padBottom = 24;
  const padSide = 10;
  const chartH = H - padTop - padBottom;
  const minScore = 88;
  const maxScore = 100;
  const range = maxScore - minScore;
  const n = data.length;
  const slotW = (W - padSide * 2) / n;
  const barW = Math.floor(slotW * 0.52);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} aria-hidden>
      {[90, 94, 98].map((v) => {
        const y = padTop + chartH - ((v - minScore) / range) * chartH;
        return <line key={v} x1={padSide} x2={W - padSide} y1={y} y2={y} stroke="#e5e7eb" strokeWidth={1} />;
      })}
      {data.map((d, i) => {
        const barH = Math.max(2, ((d.score - minScore) / range) * chartH);
        const x = padSide + i * slotW + (slotW - barW) / 2;
        const y = padTop + chartH - barH;
        const cx = x + barW / 2;
        return (
          <g key={d.label}>
            <rect x={x} y={y} width={barW} height={barH} rx={3} fill="#1D9E75" />
            <text x={cx} y={y - 5} textAnchor="middle" fontSize={12} fill="#374151">{d.score}</text>
            <text x={cx} y={H - 4} textAnchor="middle" fontSize={11} fill="#9ca3af">{d.label}</text>
          </g>
        );
      })}
    </svg>
  );
}
