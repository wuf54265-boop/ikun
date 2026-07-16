import type { RegressionCoeff } from "@/lib/types";

/** OLS 回归系数表：p<0.05 的行绿色高亮（统计显著）。 */
export function CoefficientTable({ coefficients }: { coefficients: RegressionCoeff[] }) {
  if (!coefficients.length) {
    return <p className="text-sm text-slate-400">暂无系数</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
            <th className="py-2 pr-4 font-medium">变量</th>
            <th className="py-2 pr-4 font-medium">系数</th>
            <th className="py-2 pr-4 font-medium">标准误</th>
            <th className="py-2 pr-4 font-medium">t</th>
            <th className="py-2 pr-4 font-medium">p 值</th>
          </tr>
        </thead>
        <tbody>
          {coefficients.map((c) => {
            const sig = c.p_value !== null && c.p_value < 0.05;
            return (
              <tr
                key={c.name}
                className={sig ? "border-b border-slate-100 bg-green-50" : "border-b border-slate-100"}
              >
                <td className="py-2 pr-4 font-medium text-slate-700">
                  {c.name}
                  {sig && <span className="ml-1 text-green-600">●</span>}
                </td>
                <td className="py-2 pr-4 tabular-nums">{c.coef.toFixed(4)}</td>
                <td className="py-2 pr-4 tabular-nums">
                  {c.std_err === null ? "—" : c.std_err.toFixed(4)}
                </td>
                <td className="py-2 pr-4 tabular-nums">{c.t === null ? "—" : c.t.toFixed(3)}</td>
                <td className="py-2 pr-4 tabular-nums">
                  {c.p_value === null ? "—" : c.p_value.toFixed(4)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-slate-400">● = p&lt;0.05 统计显著（系数显著异于 0）</p>
    </div>
  );
}
