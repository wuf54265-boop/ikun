"use client";

import { useState } from "react";

import type { ColumnInfo } from "@/lib/types";

const TYPE_LABEL: Record<string, { text: string; cls: string }> = {
  numeric: { text: "数值", cls: "bg-emerald-50 text-emerald-700" },
  categorical: { text: "类别", cls: "bg-amber-50 text-amber-700" },
  datetime: { text: "日期", cls: "bg-violet-50 text-violet-700" },
  boolean: { text: "布尔", cls: "bg-sky-50 text-sky-700" },
  text: { text: "文本", cls: "bg-slate-100 text-slate-600" },
};

function TypeBadge({ type }: { type: string }) {
  const t = TYPE_LABEL[type] ?? TYPE_LABEL.text;
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${t.cls}`}>
      {t.text}
    </span>
  );
}

// 数据预览表格：展示前 N 行，分页；列头显示类型标签
export function DataPreview({
  columns,
  preview,
}: {
  columns: ColumnInfo[];
  preview: Record<string, unknown>[];
}) {
  const [page, setPage] = useState(0);
  const pageSize = 10;
  const total = preview.length;
  const start = page * pageSize;
  const rows = preview.slice(start, start + pageSize);

  if (total === 0) return null;

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((c) => (
                <th key={c.name} className="whitespace-nowrap px-3 py-2 text-left">
                  <div className="font-semibold text-slate-700">{c.name}</div>
                  <div className="mt-1">
                    <TypeBadge type={c.inferred_type} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-slate-100">
                {columns.map((c) => (
                  <td
                    key={c.name}
                    className="whitespace-nowrap px-3 py-2 text-slate-600"
                  >
                    {row[c.name] === null || row[c.name] === undefined
                      ? "—"
                      : String(row[c.name])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {total > pageSize && (
        <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
          <span>
            第 {start + 1}–{Math.min(start + pageSize, total)} 行 / 共 {total} 行预览
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
            >
              上一页
            </button>
            <button
              onClick={() =>
                setPage((p) => Math.min(Math.ceil(total / pageSize) - 1, p + 1))
              }
              disabled={start + pageSize >= total}
              className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
