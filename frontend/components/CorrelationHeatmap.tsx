"use client";

import { useState } from "react";

interface Props {
  columns: string[];
  matrix: (number | null)[][];
  pValues: (number | null)[][];
}

// 将 |r| 映射为颜色：红=正相关，蓝=负相关，深度随 |r| 增加
function cellColor(r: number | null): string {
  if (r === null || Number.isNaN(r)) return "#f1f5f9"; // 未定义（常数列）
  const a = Math.min(1, Math.abs(r)) * 0.85 + 0.1; // alpha 0.1~0.95
  if (r >= 0) {
    // 正相关：红
    return `rgba(220, 38, 38, ${a})`;
  }
  // 负相关：蓝
  return `rgba(37, 99, 235, ${a})`;
}

function significance(r: number | null, p: number | null): string {
  if (p === null || p === undefined || Number.isNaN(p)) return "";
  if (p < 0.01) return "**";
  if (p < 0.05) return "*";
  return "";
}

export function CorrelationHeatmap({ columns, matrix, pValues }: Props) {
  const [hover, setHover] = useState<{ i: number; j: number } | null>(null);

  if (!columns.length) return null;

  return (
    <div className="relative">
      <div
        className="grid gap-[2px]"
        style={{ gridTemplateColumns: `120px repeat(${columns.length}, 1fr)` }}
      >
        {/* 左上角空 cell */}
        <div />
        {/* 列表头 */}
        {columns.map((c) => (
          <div
            key={`h-${c}`}
            className="truncate px-1 py-1 text-center text-[11px] font-medium text-slate-600"
            title={c}
          >
            {c}
          </div>
        ))}

        {/* 行 */}
        {columns.map((rowName, i) => (
          <div key={`row-${rowName}`} className="contents">
            <div
              className="flex items-center truncate px-1 py-1 text-[11px] font-medium text-slate-600"
              title={rowName}
            >
              {rowName}
            </div>
            {columns.map((colName, j) => {
              const r = matrix[i]?.[j] ?? null;
              const p = pValues[i]?.[j] ?? null;
              const isDiag = i === j;
              const isHover = hover && hover.i === i && hover.j === j;
              return (
                <div
                  key={`${rowName}-${colName}`}
                  className="relative flex h-12 items-center justify-center rounded text-[11px] font-semibold tabular-nums"
                  style={{
                    backgroundColor: isDiag ? "#e2e8f0" : cellColor(r),
                    color: r !== null && Math.abs(r) > 0.55 ? "#fff" : "#334155",
                    outline: isHover ? "2px solid #0f172a" : "none",
                  }}
                  onMouseEnter={() => setHover({ i, j })}
                  onMouseLeave={() => setHover(null)}
                  title={
                    isDiag
                      ? `${rowName} = ${rowName}`
                      : `${rowName} vs ${colName}\nr = ${r === null ? "未定义" : r.toFixed(4)}\np = ${
                          p === null ? "未定义" : p.toFixed(4)
                        }`
                  }
                >
                  {isDiag ? "1" : r === null ? "—" : r.toFixed(2)}
                  {!isDiag && <span className="ml-0.5 text-[9px]">{significance(r, p)}</span>}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* 图例 */}
      <div className="mt-3 flex items-center gap-3 text-[11px] text-slate-500">
        <span>负相关</span>
        <div className="h-3 w-24 rounded" style={{ background: "linear-gradient(90deg, rgba(37,99,235,0.95), rgba(37,99,235,0.1))" }} />
        <span>0</span>
        <div className="h-3 w-24 rounded" style={{ background: "linear-gradient(90deg, rgba(220,38,38,0.1), rgba(220,38,38,0.95))" }} />
        <span>正相关</span>
        <span className="ml-2">* p&lt;0.05&nbsp;&nbsp;** p&lt;0.01&nbsp;&nbsp;— 未定义(常数列)</span>
      </div>

      {hover && hover.i !== hover.j && (
        <div className="mt-2 rounded bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <b>{columns[hover.i]}</b> vs <b>{columns[hover.j]}</b>：r ={" "}
          {matrix[hover.i][hover.j] === null
            ? "未定义"
            : (matrix[hover.i][hover.j] as number).toFixed(4)}
          ，p ={" "}
          {pValues[hover.i][hover.j] === null
            ? "未定义"
            : (pValues[hover.i][hover.j] as number).toFixed(4)}
          {significance(matrix[hover.i][hover.j], pValues[hover.i][hover.j]) &&
            ` （显著${significance(matrix[hover.i][hover.j], pValues[hover.i][hover.j])}）`}
        </div>
      )}
    </div>
  );
}
