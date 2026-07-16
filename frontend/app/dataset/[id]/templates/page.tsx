"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AnalysisWizard } from "@/components/AnalysisWizard";
import { getProfile, postFunnel, postRFM } from "@/lib/api";
import type { FieldProfile, FunnelData, RFMData } from "@/lib/types";

const SEGMENT_COLORS: Record<string, string> = {
  冠军客户: "#16a34a",
  潜力客户: "#0891b2",
  忠诚客户: "#7c3aed",
  流失风险: "#f59e0b",
  已流失: "#dc2626",
  一般客户: "#64748b",
};

type Tab = "rfm" | "funnel";

export default function TemplatesPage({ params }: { params: { id: string } }) {
  const datasetId = params.id;
  const [tab, setTab] = useState<Tab>("rfm");

  const [fields, setFields] = useState<FieldProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getProfile(datasetId)
      .then((res) => {
        if (active) setFields(res.data.fields);
      })
      .catch((e) => {
        if (active) setError(String(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [datasetId]);

  return (
    <div className="flex gap-6">
      <AnalysisWizard datasetId={datasetId} />
      <section className="flex-1 rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">行业模板</h2>
        <p className="mt-1 text-sm text-slate-600">
          RFM 用户分层、转化漏斗等电商高频分析，开箱即用。
        </p>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
            字段信息加载失败：{error}
          </div>
        )}

        <div className="mt-4 flex gap-2">
          {(["rfm", "funnel"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={
                "rounded-lg px-4 py-2 text-sm font-medium " +
                (tab === t
                  ? "bg-blue-600 text-white"
                  : "border border-slate-300 text-slate-600 hover:bg-slate-100")
              }
            >
              {t === "rfm" ? "RFM 用户分层" : "漏斗转化"}
            </button>
          ))}
        </div>

        {loading && <p className="mt-4 text-sm text-slate-400">加载字段信息…</p>}

        {!loading && tab === "rfm" && (
          <RFMSection datasetId={datasetId} fields={fields} />
        )}
        {!loading && tab === "funnel" && (
          <FunnelSection datasetId={datasetId} fields={fields} />
        )}
      </section>
    </div>
  );
}

/* ---------------- RFM ---------------- */
function RFMSection({
  datasetId,
  fields,
}: {
  datasetId: string;
  fields: FieldProfile[];
}) {
  const defaults = useMemo(() => {
    const cat = fields.find((f) => f.inferred_type === "categorical")?.name ?? fields[0]?.name ?? "";
    const dt = fields.find((f) => f.inferred_type === "datetime")?.name ?? "";
    const num = fields.find((f) => f.inferred_type === "numeric")?.name ?? "";
    return { customer_id: cat, date: dt, amount: num };
  }, [fields]);

  const [customerId, setCustomerId] = useState("");
  const [date, setDate] = useState("");
  const [amount, setAmount] = useState("");
  const [snapshot, setSnapshot] = useState(new Date().toISOString().slice(0, 10));

  useEffect(() => {
    setCustomerId(defaults.customer_id);
    setDate(defaults.date);
    setAmount(defaults.amount);
  }, [defaults]);

  const [res, setRes] = useState<RFMData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = () => {
    if (!customerId || !date || !amount) {
      setErr("请先选择 客户ID / 日期 / 金额 三列");
      return;
    }
    setBusy(true);
    setErr(null);
    postRFM(datasetId, { customer_id: customerId, date, amount, snapshot_date: snapshot })
      .then((r) => setRes(r.data))
      .catch((e) => setErr(String(e)))
      .finally(() => setBusy(false));
  };

  const pieData = (res?.segments ?? []).filter((s) => s.count > 0);

  return (
    <div className="mt-4 space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Labeled label="客户ID列">
          <Select value={customerId} onChange={setCustomerId} options={fields.map((f) => f.name)} />
        </Labeled>
        <Labeled label="日期列">
          <Select value={date} onChange={setDate} options={fields.map((f) => f.name)} />
        </Labeled>
        <Labeled label="金额列">
          <Select value={amount} onChange={setAmount} options={fields.map((f) => f.name)} />
        </Labeled>
        <Labeled label="快照日期">
          <input
            type="date"
            value={snapshot}
            onChange={(e) => setSnapshot(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </Labeled>
      </div>

      <button
        onClick={run}
        disabled={busy}
        className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {busy ? "分析中…" : "运行 RFM 分析"}
      </button>

      {err && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{err}</div>}

      {res && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-700">分群占比</h3>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="count"
                    nameKey="segment"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={(d: { segment: string; count: number }) => `${d.segment} ${d.count}`}
                  >
                    {pieData.map((s) => (
                      <Cell key={s.segment} fill={SEGMENT_COLORS[s.segment] ?? "#94a3b8"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-700">分群明细</h3>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-slate-500">
                    <th className="py-1">分群</th>
                    <th>人数</th>
                    <th>占比</th>
                  </tr>
                </thead>
                <tbody>
                  {res.segments.map((s) => (
                    <tr key={s.segment} className="border-b">
                      <td className="py-1">
                        <span
                          className="mr-2 inline-block h-2 w-2 rounded-full"
                          style={{ background: SEGMENT_COLORS[s.segment] ?? "#94a3b8" }}
                        />
                        {s.segment}
                      </td>
                      <td>{s.count}</td>
                      <td>{(s.share * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl bg-slate-50 p-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">运营建议</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
              {res.suggestions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

/* ---------------- 漏斗 ---------------- */
function FunnelSection({
  datasetId,
  fields,
}: {
  datasetId: string;
  fields: FieldProfile[];
}) {
  const [available, setAvailable] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    setAvailable(fields.map((f) => f.name));
    // 默认选前 4 列作为漏斗步骤示例
    setSelected(fields.slice(0, 4).map((f) => f.name));
  }, [fields]);

  const [res, setRes] = useState<FunnelData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const addStep = (col: string) => {
    setSelected((s) => (s.includes(col) ? s : [...s, col]));
    setAvailable((a) => a.filter((c) => c !== col));
  };
  const removeStep = (col: string) => {
    setSelected((s) => s.filter((c) => c !== col));
    setAvailable((a) => [...a, col]);
  };
  const move = (idx: number, dir: -1 | 1) => {
    setSelected((s) => {
      const next = [...s];
      const j = idx + dir;
      if (j < 0 || j >= next.length) return s;
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });
  };

  const run = () => {
    if (selected.length < 2) {
      setErr("漏斗至少需 2 个步骤");
      return;
    }
    setBusy(true);
    setErr(null);
    postFunnel(datasetId, { steps: selected })
      .then((r) => setRes(r.data))
      .catch((e) => setErr(String(e)))
      .finally(() => setBusy(false));
  };

  const bottleneck = res?.bottleneck ?? null;

  return (
    <div className="mt-4 space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-xl bg-slate-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-700">可选列（点击加入漏斗）</h3>
          <div className="flex flex-wrap gap-2">
            {available.map((c) => (
              <button
                key={c}
                onClick={() => addStep(c)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-white"
              >
                + {c}
              </button>
            ))}
            {available.length === 0 && <span className="text-sm text-slate-400">已全部加入</span>}
          </div>
        </div>

        <div className="rounded-xl bg-slate-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-700">漏斗步骤（按顺序排列）</h3>
          <ol className="space-y-1">
            {selected.map((c, i) => (
              <li key={c} className="flex items-center justify-between rounded bg-white px-3 py-1.5 text-sm">
                <span>
                  {i + 1}. {c}
                </span>
                <span className="flex gap-2 text-slate-400">
                  <button onClick={() => move(i, -1)} className="hover:text-slate-700">↑</button>
                  <button onClick={() => move(i, 1)} className="hover:text-slate-700">↓</button>
                  <button onClick={() => removeStep(c)} className="hover:text-red-600">✕</button>
                </span>
              </li>
            ))}
            {selected.length === 0 && <span className="text-sm text-slate-400">尚未选择步骤</span>}
          </ol>
        </div>
      </div>

      <button
        onClick={run}
        disabled={busy}
        className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {busy ? "分析中…" : "运行漏斗分析"}
      </button>

      {err && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{err}</div>}

      {res && (
        <>
          <div className="rounded-xl bg-slate-50 p-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">漏斗转化</h3>
            <ResponsiveContainer width="100%" height={Math.max(160, res.steps.length * 56)}>
              <BarChart data={res.steps} layout="vertical" margin={{ left: 40, right: 40 }}>
                <XAxis type="number" allowDecimals={false} />
                <YAxis type="category" dataKey="step" width={80} />
                <Tooltip formatter={(v: number) => [`${v} 人`, "到达人数"]} />
                <Bar dataKey="users">
                  {res.steps.map((s) => (
                    <Cell key={s.step} fill={bottleneck?.includes(s.step) ? "#dc2626" : "#2563eb"} />
                  ))}
                  <LabelList dataKey="users" position="right" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {bottleneck && (
              <p className="mt-2 text-sm text-red-700">
                流失最大瓶颈：{bottleneck}
              </p>
            )}
          </div>

          <div className="rounded-xl bg-slate-50 p-4">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-slate-500">
                  <th className="py-1">步骤</th>
                  <th>到达人数</th>
                  <th>总体转化率</th>
                </tr>
              </thead>
              <tbody>
                {res.steps.map((s) => (
                  <tr key={s.step} className="border-b">
                    <td className="py-1">{s.step}</td>
                    <td>{s.users}</td>
                    <td>{s.conversion.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

/* ---------------- 小组件 ---------------- */
function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-600">{label}</span>
      {children}
    </label>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
    >
      <option value="">（选择列）</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
