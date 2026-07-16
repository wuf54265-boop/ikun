"use client";

import { useMemo, useState } from "react";
import type {
  AnomalyData,
  AnomalyMethod,
  AnomalyRequest,
  FieldProfile,
} from "@/lib/types";

interface Props {
  numericColumns: string[];
  fields: FieldProfile[];
  onDetect: (req: AnomalyRequest) => void;
  result: AnomalyData | null;
}

const METHODS: { key: AnomalyMethod; label: string; hint: string }[] = [
  { key: "iqr", label: "IQR", hint: "异常 if x < Q1 - k·IQR 或 x > Q3 + k·IQR（纯 NumPy 自实现）" },
  { key: "zscore", label: "Z-score", hint: "z = (x-μ)/σ，|z| > threshold 判异常（纯 NumPy 自实现）" },
  {
    key: "isolation_forest",
    label: "Isolation Forest",
    hint: "sklearn 封装：多变量集成检测，单点解释性弱于 IQR/Z-score",
  },
];

function MiniBoxPlot({
  min,
  q1,
  median,
  q3,
  max,
  outliers,
}: {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  outliers: number[];
}) {
  const all = [min, max, ...outliers];
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const span = hi - lo || 1;
  const x0 = lo - span * 0.1;
  const x1 = hi + span * 0.1;
  const W = 280;
  const H = 56;
  const mid = H / 2;
  const sx = (v: number) => ((v - x0) / (x1 - x0)) * W;
  return (
    <svg width={W} height={H} className="overflow-visible">
      <line x1={sx(min)} y1={mid} x2={sx(q1)} y2={mid} stroke="#94a3b8" />
      <line x1={sx(q3)} y1={mid} x2={sx(max)} y2={mid} stroke="#94a3b8" />
      <rect
        x={sx(q1)}
        y={mid - 12}
        width={Math.max(1, sx(q3) - sx(q1))}
        height={24}
        fill="#dbeafe"
        stroke="#3b82f6"
      />
      <line x1={sx(median)} y1={mid - 12} x2={sx(median)} y2={mid + 12} stroke="#1d4ed8" strokeWidth={2} />
      <line x1={sx(min)} y1={mid - 6} x2={sx(min)} y2={mid + 6} stroke="#94a3b8" />
      <line x1={sx(max)} y1={mid - 6} x2={sx(max)} y2={mid + 6} stroke="#94a3b8" />
      {outliers.map((o, i) => (
        <circle key={i} cx={sx(o)} cy={mid} r={3} fill="#ef4444" />
      ))}
    </svg>
  );
}

export function AnomalyPanel({ numericColumns, fields, onDetect, result }: Props) {
  const [method, setMethod] = useState<AnomalyMethod>("iqr");
  const [k, setK] = useState(1.5);
  const [threshold, setThreshold] = useState(3.0);
  const [contamination, setContamination] = useState(0.1);
  const [selected, setSelected] = useState<string[]>(numericColumns);

  const paramValue = method === "iqr" ? k : method === "zscore" ? threshold : contamination;

  const toggleCol = (c: string) =>
    setSelected((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));

  const handleDetect = () => {
    onDetect({
      method,
      columns: selected,
      threshold: paramValue,
    });
  };

  // 按列汇总异常点（含箱线图所需的分位数与异常值）
  const byColumn = useMemo(() => {
    if (!result) return [];
    const map = new Map<string, { count: number; outliers: number[] }>();
    for (const a of result.anomalies) {
      const e = map.get(a.column) ?? { count: 0, outliers: [] };
      e.count += 1;
      if (a.value != null && !Number.isNaN(a.value)) e.outliers.push(a.value);
      map.set(a.column, e);
    }
    return Array.from(map.entries());
  }, [result]);

  const fieldByName = useMemo(() => {
    const m = new Map<string, FieldProfile>();
    for (const f of fields) m.set(f.name, f);
    return m;
  }, [fields]);

  return (
    <div className="space-y-4">
      {/* 方法 tab */}
      <div className="flex gap-2">
        {METHODS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMethod(m.key)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              method === m.key
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        {METHODS.find((m) => m.key === method)?.hint}
      </p>

      {/* 参数滑块 */}
      <div className="flex items-center gap-3">
        <label className="w-28 text-sm text-slate-600">
          {method === "iqr"
            ? "k（默认 1.5）"
            : method === "zscore"
            ? "threshold（默认 3.0）"
            : "contamination（默认 0.1）"}
        </label>
        <input
          type="range"
          min={method === "isolation_forest" ? 0.01 : method === "iqr" ? 0.5 : 1.0}
          max={method === "isolation_forest" ? 0.5 : 5.0}
          step={method === "isolation_forest" ? 0.01 : 0.1}
          value={paramValue}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (method === "iqr") setK(v);
            else if (method === "zscore") setThreshold(v);
            else setContamination(v);
          }}
          className="flex-1"
        />
        <span className="w-12 text-right tabular-nums text-sm text-slate-700">
          {paramValue.toFixed(2)}
        </span>
      </div>

      {/* 数值列多选 */}
      <div>
        <div className="mb-1 text-xs font-medium text-slate-500">检测列（数值列）</div>
        <div className="flex flex-wrap gap-2">
          {numericColumns.length === 0 && (
            <span className="text-xs text-slate-400">无数值列</span>
          )}
          {numericColumns.map((c) => (
            <label
              key={c}
              className={`cursor-pointer rounded-full border px-3 py-1 text-xs ${
                selected.includes(c)
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-slate-300 text-slate-600"
              }`}
            >
              <input
                type="checkbox"
                className="mr-1 hidden"
                checked={selected.includes(c)}
                onChange={() => toggleCol(c)}
              />
              {c}
            </label>
          ))}
        </div>
      </div>

      <button
        onClick={handleDetect}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        检测异常
      </button>

      {/* 结果 */}
      {result && (
        <div className="space-y-4 border-t border-slate-200 pt-4">
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-700">
              共 {result.anomaly_count} 个异常点
            </span>
            <span className="text-xs text-slate-500">方法：{result.method}</span>
          </div>

          {/* 各列分布 + 箱线图 */}
          {result.method !== "isolation_forest" && (
            <div className="space-y-3">
              {byColumn.map(([col, info]) => {
                const f = fieldByName.get(col);
                if (
                  !f ||
                  f.min == null ||
                  f.q1 == null ||
                  f.median == null ||
                  f.q3 == null ||
                  f.max == null
                ) {
                  return (
                    <div key={col} className="text-sm text-slate-600">
                      {col}：{info.count} 个异常
                    </div>
                  );
                }
                return (
                  <div key={col} className="rounded-lg border border-slate-200 p-3">
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-700">{col}</span>
                      <span className="text-xs text-red-600">{info.count} 异常</span>
                    </div>
                    <MiniBoxPlot
                      min={f.min as number}
                      q1={f.q1 as number}
                      median={f.median as number}
                      q3={f.q3 as number}
                      max={f.max as number}
                      outliers={info.outliers}
                    />
                  </div>
                );
              })}
            </div>
          )}

          {/* 异常点表格 */}
          <div className="max-h-72 overflow-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">列</th>
                  <th className="px-3 py-2 text-right">行号</th>
                  <th className="px-3 py-2 text-right">值</th>
                  <th className="px-3 py-2 text-right">分数</th>
                </tr>
              </thead>
              <tbody>
                {result.anomalies.map((a, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-3 py-1.5 text-slate-700">{a.column}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums text-slate-600">
                      {a.index}
                    </td>
                    <td className="px-3 py-1.5 text-right tabular-nums text-slate-600">
                      {a.value == null || Number.isNaN(a.value) ? "—" : a.value.toFixed(2)}
                    </td>
                    <td className="px-3 py-1.5 text-right tabular-nums text-red-600">
                      {a.score == null || Number.isNaN(a.score) ? "—" : a.score.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
