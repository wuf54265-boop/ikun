"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { AnalysisWizard } from "@/components/AnalysisWizard";
import { ExplainPanel } from "@/components/ExplainPanel";
import { CorrelationHeatmap } from "@/components/CorrelationHeatmap";
import { getProfile, postCorrelation, postHypothesis, postDistribution } from "@/lib/api";
import { useAnalysisStore } from "@/store/useAnalysisStore";
import type {
  AnalysisResponse,
  CorrelationData,
  DistributionData,
  FieldProfile,
  HypothesisData,
  ProfileResponse,
} from "@/lib/types";

type Envelope<T> = AnalysisResponse<T>;

export default function StatsPage({ params }: { params: { id: string } }) {
  const datasetId = params.id;
  const [fields, setFields] = useState<FieldProfile[]>([]);
  const [rows, setRows] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getProfile(datasetId)
      .then((res: Envelope<ProfileResponse>) => {
        if (active) {
          setFields(res.data.fields);
          setRows(res.data.rows);
        }
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

  const numericCols = useMemo(
    () => fields.filter((f) => f.inferred_type === "numeric").map((f) => f.name),
    [fields]
  );
  const catCols = useMemo(
    () =>
      fields
        .filter((f) => f.inferred_type === "categorical" || f.inferred_type === "boolean")
        .map((f) => f.name),
    [fields]
  );

  return (
    <div className="flex gap-6">
      <AnalysisWizard datasetId={datasetId} />
      <section className="flex-1 space-y-8 rounded-2xl bg-white p-6 shadow-sm">
        <div>
          <h2 className="text-xl font-semibold">统计分析</h2>
          <p className="mt-1 text-sm text-slate-600">
            相关性（Pearson 自实现）、假设检验（Welch t / 卡方 自实现）、分布检验（KS 自实现）。
            每个结果配「方法说明」可展开公式与假设。
          </p>
          {loading && <p className="mt-2 text-sm text-slate-400">加载字段信息…</p>}
          {!loading && error && (
            <div className="mt-3 rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700">
              字段信息加载失败：{error}
            </div>
          )}
        </div>

        <CorrelationSection datasetId={datasetId} numericCols={numericCols} />
        <HypothesisSection
          datasetId={datasetId}
          numericCols={numericCols}
          catCols={catCols}
        />
        <DistributionSection datasetId={datasetId} numericCols={numericCols} fields={fields} rows={rows} />
      </section>
    </div>
  );
}

/* ----------------- 相关性分析 ----------------- */
function CorrelationSection({
  datasetId,
  numericCols,
}: {
  datasetId: string;
  numericCols: string[];
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [res, setRes] = useState<Envelope<CorrelationData> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setResult = useAnalysisStore((s) => s.setResult);
  useEffect(() => {
    if (res) setResult(`stats-corr-${datasetId}`, { data: res.data, explanation: res.explanation });
  }, [res, datasetId, setResult]);

  const toggle = (c: string) =>
    setSelected((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c]));

  const run = async () => {
    setErr(null);
    if (selected.length < 2) {
      setErr("请至少选择 2 个数值列");
      return;
    }
    setBusy(true);
    try {
      const r = await postCorrelation(datasetId, { dataset_id: datasetId, type: "pearson", columns: selected });
      setRes(r);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h3 className="font-semibold">相关性分析（Pearson）</h3>
      <p className="text-xs text-slate-500">数值列多选（≥2），r 值 |r| 越大相关越强，* p&lt;0.05、** p&lt;0.01</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {numericCols.map((c) => (
          <label
            key={c}
            className={`cursor-pointer rounded-full border px-3 py-1 text-xs ${
              selected.includes(c)
                ? "border-blue-500 bg-blue-50 text-blue-700"
                : "border-slate-300 text-slate-600"
            }`}
          >
            <input type="checkbox" className="mr-1" checked={selected.includes(c)} onChange={() => toggle(c)} />
            {c}
          </label>
        ))}
        {numericCols.length === 0 && <span className="text-xs text-slate-400">无数值列</span>}
      </div>
      <button
        onClick={run}
        disabled={busy}
        className="mt-3 rounded bg-blue-600 px-4 py-1.5 text-sm text-white disabled:opacity-50"
      >
        {busy ? "计算中…" : "计算相关性"}
      </button>
      {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      {res && (
        <div className="mt-4">
          <CorrelationHeatmap columns={res.data.columns} matrix={res.data.matrix} pValues={res.data.p_values} />
          <ExplainPanel explanation={res.explanation} />
        </div>
      )}
    </div>
  );
}

/* ----------------- 假设检验 ----------------- */
function HypothesisSection({
  datasetId,
  numericCols,
  catCols,
}: {
  datasetId: string;
  numericCols: string[];
  catCols: string[];
}) {
  const [test, setTest] = useState<"welch_t" | "chi2">("welch_t");
  const [wGroup, setWGroup] = useState("");
  const [wValue, setWValue] = useState("");
  const [cRow, setCRow] = useState("");
  const [cCol, setCCol] = useState("");
  const [res, setRes] = useState<Envelope<HypothesisData> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setResult = useAnalysisStore((s) => s.setResult);
  useEffect(() => {
    if (res) setResult(`stats-hyp-${datasetId}`, { data: res.data, explanation: res.explanation });
  }, [res, datasetId, setResult]);

  const run = async () => {
    setErr(null);
    setBusy(true);
    try {
      const body =
        test === "welch_t"
          ? { dataset_id: datasetId, test, group_column: wGroup, value_column: wValue }
          : { dataset_id: datasetId, test, group_column: cRow, value_column: cCol };
      const r = await postHypothesis(datasetId, body);
      setRes(r);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h3 className="font-semibold">假设检验</h3>
      <div className="mt-3 flex gap-2 text-sm">
        <button
          className={`rounded px-3 py-1 ${test === "welch_t" ? "bg-blue-600 text-white" : "border border-slate-300 text-slate-600"}`}
          onClick={() => setTest("welch_t")}
        >
          Welch t 检验
        </button>
        <button
          className={`rounded px-3 py-1 ${test === "chi2" ? "bg-blue-600 text-white" : "border border-slate-300 text-slate-600"}`}
          onClick={() => setTest("chi2")}
        >
          卡方独立性
        </button>
      </div>

      {test === "welch_t" ? (
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
          <select value={wGroup} onChange={(e) => setWGroup(e.target.value)} className="rounded border border-slate-300 px-2 py-1">
            <option value="">分组列（二分类别）</option>
            {catCols.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select value={wValue} onChange={(e) => setWValue(e.target.value)} className="rounded border border-slate-300 px-2 py-1">
            <option value="">数值列</option>
            {numericCols.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
          <select value={cRow} onChange={(e) => setCRow(e.target.value)} className="rounded border border-slate-300 px-2 py-1">
            <option value="">行变量（类别列）</option>
            {catCols.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select value={cCol} onChange={(e) => setCCol(e.target.value)} className="rounded border border-slate-300 px-2 py-1">
            <option value="">列变量（类别列）</option>
            {catCols.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      )}

      <button
        onClick={run}
        disabled={busy}
        className="mt-3 rounded bg-blue-600 px-4 py-1.5 text-sm text-white disabled:opacity-50"
      >
        {busy ? "计算中…" : "运行检验"}
      </button>
      {err && <p className="mt-2 text-sm text-red-600">{err}</p>}

      {res && (
        <div className="mt-4">
          <ResultCard
            rows={[
              ["检验方法", res.data.test],
              ["统计量", res.data.statistic],
              ["自由度 df", res.data.df ?? "—"],
              ["p 值", res.data.p_value],
              ["效应量", res.data.effect_size ?? "—"],
            ]}
            conclusion={res.data.conclusion}
            warning={res.data.warning}
          />
          <ExplainPanel explanation={res.explanation} />
        </div>
      )}
    </div>
  );
}

/* ----------------- 分布检验 ----------------- */
function DistributionSection({
  datasetId,
  numericCols,
  fields,
  rows,
}: {
  datasetId: string;
  numericCols: string[];
  fields: FieldProfile[];
  rows: number;
}) {
  const [col, setCol] = useState("");
  const [res, setRes] = useState<Envelope<DistributionData> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setResult = useAnalysisStore((s) => s.setResult);
  useEffect(() => {
    if (res) setResult(`stats-dist-${datasetId}`, { data: res.data, explanation: res.explanation });
  }, [res, datasetId, setResult]);

  const field = fields.find((f) => f.name === col);
  const histData = useMemo(() => {
    if (!field || !field.histogram.length) return [];
    const total = field.histogram.reduce((s, b) => s + b.count, 0);
    const mean = field.mean ?? 0;
    const std = field.std ?? 1;
    return field.histogram.map((b) => {
      const center = ((b.bin_start ?? 0) + (b.bin_end ?? 0)) / 2;
      const width = (b.bin_end ?? 0) - (b.bin_start ?? 0) || 1;
      const pdf = Math.exp(-0.5 * ((center - mean) / (std || 1)) ** 2) / ((std || 1) * Math.sqrt(2 * Math.PI));
      return {
        name: center.toFixed(1),
        count: b.count,
        fit: Math.round(pdf * total * width * 10) / 10,
      };
    });
  }, [field]);

  const run = async () => {
    setErr(null);
    if (!col) {
      setErr("请选择数值列");
      return;
    }
    setBusy(true);
    try {
      const r = await postDistribution(datasetId, { dataset_id: datasetId, test: "ks", column: col });
      setRes(r);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h3 className="font-semibold">分布检验（KS 正态性 · Lilliefors 修正）</h3>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
        <select value={col} onChange={(e) => setCol(e.target.value)} className="rounded border border-slate-300 px-2 py-1">
          <option value="">数值列</option>
          {numericCols.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button
          onClick={run}
          disabled={busy}
          className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white disabled:opacity-50"
        >
          {busy ? "检验中…" : "检验正态性"}
        </button>
      </div>
      {err && <p className="mt-2 text-sm text-red-600">{err}</p>}

      {res && (
        <div className="mt-4">
          <ResultCard
            rows={[
              ["检验方法", "KS (Lilliefors)"],
              ["KS 统计量 D", res.data.statistic],
              ["近似 p 值", res.data.p_value],
              ["是否正态", res.data.is_normal ? "是（D<临界值）" : "否（D≥临界值）"],
            ]}
            conclusion={res.data.is_normal ? "在 α=0.05 下不拒绝正态性假设" : "在 α=0.05 下拒绝正态性假设"}
          />
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={histData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#93c5fd" name="实际频数" />
                <Line type="monotone" dataKey="fit" stroke="#dc2626" name="正态拟合" dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            蓝柱=实际分布（来自画像直方图），红线=按样本均值/标准差拟合的正态曲线（已缩放至频数量级）。
          </p>
          <ExplainPanel explanation={res.explanation} />
        </div>
      )}
      {rows > 0 && !res && (
        <p className="mt-2 text-[11px] text-slate-400">提示：n&gt;50 临界值 D_crit≈0.886/√n；n≤50 查 Lilliefors 表。</p>
      )}
    </div>
  );
}

/* ----------------- 通用结果卡片 ----------------- */
function ResultCard({
  rows,
  conclusion,
  warning,
}: {
  rows: [string, string | number][];
  conclusion: string;
  warning?: string | null;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
        {rows.map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <span className="text-[11px] text-slate-500">{k}</span>
            <span className="tabular-nums font-medium text-slate-700">{typeof v === "number" ? v.toFixed(4) : v}</span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-sm font-medium text-slate-800">结论：{conclusion}</p>
      {warning && <p className="mt-1 text-xs text-amber-700">⚠ {warning}</p>}
    </div>
  );
}
