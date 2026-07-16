"use client";

import { useState } from "react";

// 可解释面板：默认折叠，点击展开方法 / 假设 / 解读
export function ExplainPanel({
  explanation,
}: {
  explanation: {
    method?: string;
    assumptions?: string[];
    interpretation?: string;
    caveats?: string[];
  };
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="font-medium text-blue-600"
      >
        {open ? "收起方法说明 ▲" : "查看方法说明 ▼"}
      </button>
      {open && (
        <div className="mt-2 space-y-1 text-slate-600">
          <p>
            <span className="font-semibold">方法：</span>
            {explanation.method ?? "-"}
          </p>
          {explanation.assumptions && explanation.assumptions.length > 0 && (
            <p>
              <span className="font-semibold">假设：</span>
              {explanation.assumptions.join("；")}
            </p>
          )}
          {explanation.interpretation && (
            <p>
              <span className="font-semibold">解读：</span>
              {explanation.interpretation}
            </p>
          )}
          {explanation.caveats && explanation.caveats.length > 0 && (
            <p>
              <span className="font-semibold">局限：</span>
              {explanation.caveats.join("；")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
