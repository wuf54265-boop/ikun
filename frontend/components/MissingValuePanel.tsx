"use client";

import type { FieldProfile, MissingStrategyName } from "@/lib/types";
import { deriveMissingInfo } from "@/lib/cleaning";

export interface StrategyState {
  strategy: MissingStrategyName;
  fill: string;
}

interface Props {
  fields: FieldProfile[];
  rows: number;
  strategies: Record<string, StrategyState>;
  onStrategyChange: (col: string, strategy: MissingStrategyName, fill?: string) => void;
}

const STRATEGY_OPTIONS: { value: MissingStrategyName; label: string }[] = [
  { value: "drop", label: "删除行 (drop)" },
  { value: "mean", label: "均值 (mean)" },
  { value: "median", label: "中位数 (median)" },
  { value: "mode", label: "众数 (mode)" },
  { value: "fill", label: "自定义填充 (fill)" },
];

const RECO_BADGE: Record<string, string> = {
  keep: "bg-slate-100 text-slate-600",
  drop: "bg-blue-100 text-blue-700",
  median: "bg-emerald-100 text-emerald-700",
  mode: "bg-emerald-100 text-emerald-700",
  review: "bg-red-100 text-red-700",
};

const RECO_LABEL: Record<string, string> = {
  keep: "无需处理",
  drop: "删除行 (<5%)",
  median: "中位数填充",
  mode: "众数填充",
  review: "高缺失·人工判断",
};

export function MissingValuePanel({ fields, rows, strategies, onStrategyChange }: Props) {
  const info = deriveMissingInfo(fields, rows);
  const totalMissing = info.reduce((s, m) => s + m.missingCount, 0);

  return (
    <div className="space-y-4">
      {/* 缺失矩阵总览：每列一行，绿色=完整，黄色=缺失 */}
      <div>
        <div className="mb-1 text-xs font-medium text-slate-500">
          缺失矩阵总览（共 {totalMissing} 个缺失值）
        </div>
        <div className="space-y-1">
          {info.map((m) => (
            <div key={m.column} className="flex items-center gap-2 text-xs">
              <span className="w-32 shrink-0 truncate text-slate-600" title={m.column}>
                {m.column}
              </span>
              <div className="flex h-3 flex-1 overflow-hidden rounded bg-slate-100">
                <div
                  className="bg-emerald-400"
                  style={{ width: `${100 - m.missingRate * 100}%` }}
                />
                <div
                  className="bg-amber-300"
                  style={{ width: `${m.missingRate * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 每列策略行 */}
      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">列</th>
              <th className="px-3 py-2 text-right">缺失</th>
              <th className="px-3 py-2 text-left">缺失率</th>
              <th className="px-3 py-2 text-left">推荐</th>
              <th className="px-3 py-2 text-left">策略</th>
            </tr>
          </thead>
          <tbody>
            {info.map((m) => {
              const st = strategies[m.column];
              return (
                <tr key={m.column} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-medium text-slate-700">
                    {m.column}
                    <span className="ml-1 text-xs font-normal text-slate-400">
                      {m.dtype}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-slate-600">
                    {m.missingCount}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-24 overflow-hidden rounded bg-slate-100">
                        <div
                          className="h-full bg-amber-400"
                          style={{ width: `${Math.min(100, m.missingRate * 100)}%` }}
                        />
                      </div>
                      <span className="tabular-nums text-xs text-slate-500">
                        {(m.missingRate * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs ${
                        RECO_BADGE[m.recommended] ?? "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {RECO_LABEL[m.recommended] ?? m.recommended}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <select
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                        value={st?.strategy ?? ""}
                        onChange={(e) =>
                          onStrategyChange(
                            m.column,
                            e.target.value as MissingStrategyName,
                            st?.fill
                          )
                        }
                      >
                        <option value="">未选择</option>
                        {STRATEGY_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                      {st?.strategy === "fill" && (
                        <input
                          className="w-24 rounded border border-slate-300 px-2 py-1 text-xs"
                          placeholder="填充值"
                          value={st.fill}
                          onChange={(e) => onStrategyChange(m.column, "fill", e.target.value)}
                        />
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
