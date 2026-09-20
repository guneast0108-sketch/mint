"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, FileText, Users, Zap, ShieldCheck } from "lucide-react";
import { company, metrics, teamMembers } from "@/app/data/mock";

export default function DashboardPage() {
  const [savedKrw, setSavedKrw] = useState(metrics.savedKrw);
  const [totalCalls, setTotalCalls] = useState(metrics.totalCalls);

  useEffect(() => {
    const interval = setInterval(() => {
      setSavedKrw((prev) => prev + Math.floor(Math.random() * 5000));
      setTotalCalls((prev) => prev + Math.floor(Math.random() * 20));
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg font-medium text-emerald-700">🌿 mint</span>
            <span className="text-gray-300">|</span>
            <span className="text-sm text-gray-500">{company.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">{company.period}</span>
            <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center">
              <span className="text-xs font-medium text-emerald-700">박</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Page title */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-medium text-gray-900">팀 대시보드</h1>
            <p className="text-sm text-gray-400 mt-0.5">{company.teamSize}명 · {company.period}</p>
          </div>
          <Link
            href="/dashboard/quality"
            className="flex items-center gap-1.5 px-4 py-2 rounded-md border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <FileText size={14} />
            상세 리포트
          </Link>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="이번 달 절감액"
            value={`₩${savedKrw.toLocaleString()}`}
            sub={`전월 대비 ${metrics.savedChange}%`}
            trend="down"
            icon={<Zap size={16} />}
            highlight
          />
          <MetricCard
            label="총 API 호출"
            value={`${totalCalls.toLocaleString()}건`}
            sub={`팀 평균 ${metrics.avgPerMember.toLocaleString()}건`}
            icon={<ArrowUpRight size={16} />}
          />
          <MetricCard
            label="평균 절감률"
            value={`${metrics.savingsRate}%`}
            sub="캐싱 31% / 라우팅 14% / 압축 8%"
            icon={<Users size={16} />}
          />
          <MetricCard
            label="품질 점수"
            value={`${metrics.qualityScore}/100`}
            sub={`미적용 대비 동등 ${metrics.qualityBaseline}%`}
            icon={<ShieldCheck size={16} />}
          />
        </div>

        {/* Savings breakdown */}
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-medium text-gray-700 mb-4">절감 모듈별 기여</h2>
          <div className="space-y-3">
            {[
              { label: "Caching",     pct: 31, color: "bg-emerald-500" },
              { label: "Routing",     pct: 14, color: "bg-indigo-400" },
              { label: "Compression", pct: 8,  color: "bg-amber-400" },
            ].map(({ label, pct, color }) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-sm text-gray-500 w-24">{label}</span>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full ${color} rounded-full`} style={{ width: `${(pct / 53) * 100}%` }} />
                </div>
                <span className="text-sm font-medium text-gray-700 w-8 text-right">{pct}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Team table */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">팀원별 현황 (상위 5명)</h2>
            <span className="text-xs text-gray-400">사용량 기준</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {["이름", "역할", "API 호출", "원가", "절감액", "품질"].map((h) => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-medium text-gray-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {teamMembers.map((m, i) => (
                <tr key={m.name} className={i < teamMembers.length - 1 ? "border-b border-gray-100" : ""}>
                  <td className="px-5 py-3.5 font-medium text-gray-900">{m.name}</td>
                  <td className="px-5 py-3.5">
                    <span className="px-2 py-0.5 rounded-md bg-gray-100 text-xs text-gray-600">{m.role}</span>
                  </td>
                  <td className="px-5 py-3.5 text-gray-600">{m.calls.toLocaleString()}</td>
                  <td className="px-5 py-3.5 text-gray-600">₩{m.costKrw.toLocaleString()}</td>
                  <td className="px-5 py-3.5 font-medium text-emerald-700">-₩{m.savedKrw.toLocaleString()}</td>
                  <td className="px-5 py-3.5">
                    <QualityBadge score={m.quality} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

function MetricCard({
  label, value, sub, icon, trend, highlight,
}: {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  trend?: "up" | "down";
  highlight?: boolean;
}) {
  return (
    <div className={`rounded-lg border p-5 ${highlight ? "bg-emerald-50 border-emerald-100" : "bg-white border-gray-200"}`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs font-medium ${highlight ? "text-emerald-700" : "text-gray-500"}`}>{label}</span>
        <span className={highlight ? "text-emerald-600" : "text-gray-400"}>{icon}</span>
      </div>
      <div className={`text-2xl font-medium mb-1 ${highlight ? "text-emerald-800" : "text-gray-900"}`}>{value}</div>
      <div className="flex items-center gap-1">
        {trend === "down" && <ArrowDownRight size={12} className="text-emerald-600" />}
        <span className="text-xs text-gray-400">{sub}</span>
      </div>
    </div>
  );
}

function QualityBadge({ score }: { score: number }) {
  const color = score >= 95 ? "text-emerald-700 bg-emerald-50" : score >= 93 ? "text-indigo-600 bg-indigo-50" : "text-gray-600 bg-gray-100";
  return (
    <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${color}`}>{score}</span>
  );
}
