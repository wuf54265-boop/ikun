"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// 分析向导侧边栏：概览 → 清洗 → 统计 → 建模 → 模板 → 报告
// 根据当前路径高亮所在步骤
const STEPS = [
  ["overview", "数据概览"],
  ["clean", "数据清洗"],
  ["stats", "统计分析"],
  ["model", "建模分析"],
  ["templates", "行业模板"],
  ["report", "AI 报告"],
] as const;

export function AnalysisWizard({ datasetId }: { datasetId: string }) {
  const pathname = usePathname();
  const activeKey = STEPS.find(([key]) =>
    pathname.includes(`/dataset/${datasetId}/${key}`)
  )?.[0];

  return (
    <nav className="w-44 shrink-0">
      <ul className="space-y-1 text-sm">
        {STEPS.map(([key, label]) => {
          const active = key === activeKey;
          return (
            <li key={key}>
              <Link
                href={`/dataset/${datasetId}/${key}`}
                className={`block rounded-lg px-3 py-2 ${
                  active
                    ? "bg-blue-50 font-semibold text-blue-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
