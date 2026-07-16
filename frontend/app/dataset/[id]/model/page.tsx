"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
} from "recharts";
import { AnalysisWizard } from "@/components/AnalysisWizard";
import { ExplainPanel } from "@/components/ExplainPanel";
import { CoefficientTable } from "@/components/CoefficientTable";
import { ClusterChart } from "@/components/ClusterChart";
import { getProfile, postRegression, postClustering } from "@/lib/api";
import { useAnalysisStore } from "@/store/useAnalysisStore";
import type {
  AnalysisResponse,
  ClusteringData,
  FieldProfile,
  ProfileResponse,
  RegressionData,
} from "@/lib/types";

type Envelope<T> = AnalysisResponse<T>;

export default function ModelPage({ params }: { params: { id: string } }) {
  const datasetId = params.id;
  const [fields, setFields] = useState<FieldProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getProfile(datasetId)
      .then((res: Envelope<ProfileResponse>) => {
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

  const numericCols = useMemo(
    () => fields.filter((f) => f.inferred_type === "numeric").map((f) => f.name),
    [fields]
  );

  return (
    <div className="flex gap-6">
      <AnalysisWizard datasetId={datasetId} />
      <section className="flex-1 space-y-8 rounded-2xl bg-white p-6 shadow-sm">
        <div>
          <h2 className="text-xl font-semibold">建模分析</h2>
          <p className="mt-1 text-sm text-slate-600">
            OLS 线性回归（正规方程自实现，含标准误/t/p/R² + 残差诊断）；K-Means 聚类
            （k-means++ 初始化自实现，肘部 + 轮廓系数选 K）。
          </p>
          {loading && <p className="mt-2 text-sm text-slate-400">加载字段信息…</p>}
          {!loading && error && (
            <div className="mt-3 rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700">
              字段信息加载失败：{error}
            </div>
          )}
        </div>

        {!loading && !error && (
          <>
            <RegressionSection datasetId={datasetId} numericCols={numericCols} />
            <ClusteringSection datasetId={datasetId} numericCols={numericCols} />
          </>
        )}
      </section>
    </div>
  );
}

/* ----------------- OLS 回归 ----------------- */
function RegressionSection({
  datasetId,
  numericCols,
}: {
  datasetId: string;
  numericCols: string[];
}) {
  const [target, setTarget] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [standardize, setStandardize] = useState(false);
  const [res, setRes] = useState<Envelope<RegressionData> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setResult = useAnalysisStore((s) => s.setResult);
  useEffect(() => {
    if (res) setResult(`model-reg-${datasetId}`, { data: res.data, explanation: res.explanation });
  }, [res, datasetId, setResult]);

  const toggle = (c: string) =>
    setSelected((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c]));

  const run = async () => {
    setErr(null);
    if (!target) {
      setErr("请选择目标变量（因变量）");
      return;
    }
    setBusy(true);
    try {
      const r = await postRegression(datasetId, {
        dataset_id: datasetId,
        target,
        features: selected.filter((c) => c !== target),
        standardize,
      });
      setRes(r);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const residualData = res
    ? res.data.residual_plot.residuals.map((rv, i) => ({
        fitted: res.data.residual_plot.fitted[i],
        residual: rv,
      }))
    : [];
  const qqData = res ? res.data.residual_plot.qq_data : [];
  // Q-Q 图 y=x 参考线（取数据范围端点）
  const qqLine =
    qqData.length > 1
      ? (() => {
          const vals = qqData.flatMap((p) => [p.theoretical, p.sample]);
          const lo = Math.min(...vals);
          const hi = Math.max(...vals);
          return [
            { x: lo, y: lo },
            { x: hi, y: hi },
          ] as { x: number; y: number }[];
        })()
      : null;

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h3 className="font-semibold">OLS 线性回归</h3>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          className="rounded border border-slate-300 px-2 py-1"
        >
          <option value="">目标变量（因变量）</option>
          {numericCols.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={standardize}
            onChange={(e) => setStandardize(e.target.checked)}
          />
          标准化系数（比较特征重要性）
        </label>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {numericCols
          .filter((c) => c !== target)
          .map((c) => (
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
                className="mr-1"
                checked={selected.includes(c)}
                onChange={() => toggle(c)}
              />
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
        {busy ? "计算中…" : "运行回归"}
      </button>
      {err && <p className="mt-2 text-sm text-red-600">{err}</p>}

      {res && (
        <div className="mt-4 space-y-4">
          {res.data.warning && (
            <p className="rounded bg-amber-50 px-3 py-2 text-xs text-amber-700">
              ⚠ {res.data.warning}
            </p>
          )}
          <CoefficientTable coefficients={res.data.coefficients} />
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3">
              <div className="flex flex-col">
                <span className="text-[11px] text-slate-500">R²</span>
                <span className="tabular-nums font-medium text-slate-700">
                  {res.data.r_squared.toFixed(4)}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[11px] text-slate-500">调整 R²</span>
                <span className="tabular-nums font-medium text-slate-700">
                  {res.data.adj_r_squared.toFixed(4)}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 p-3">
              <h4 className="mb-2 text-sm font-medium">残差 vs 拟合值</h4>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="fitted" name="拟合值" />
                    <YAxis type="number" dataKey="residual" name="残差" />
                    <ZAxis range={[40, 40]} />
                    <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                    <ReferenceLine y={0} stroke="#dc2626" strokeDasharray="4 2" />
                    <Scatter data={residualData} fill="#2563eb" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <h4 className="mb-2 text-sm font-medium">Q-Q 图（残差正态性）</h4>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="theoretical" name="理论分位" />
                    <YAxis type="number" dataKey="sample" name="实际分位" />
                    <ZAxis range={[40, 40]} />
                    <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                    {qqLine && <ReferenceLine stroke="#dc2626" strokeDasharray="4 2" segment={qqLine} />}
                    <Scatter data={qqData} fill="#16a34a" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <ExplainPanel explanation={res.explanation} />
        </div>
      )}
    </div>
  );
}

/* ----------------- K-Means 聚类 ----------------- */
function ClusteringSection({
  datasetId,
  numericCols,
}: {
  datasetId: string;
  numericCols: string[];
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [autoK, setAutoK] = useState(true);
  const [manualK, setManualK] = useState(3);
  const [res, setRes] = useState<Envelope<ClusteringData> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setResult = useAnalysisStore((s) => s.setResult);
  useEffect(() => {
    if (res) setResult(`model-cluster-${datasetId}`, { data: res.data, explanation: res.explanation });
  }, [res, datasetId, setResult]);

  const toggle = (c: string) =>
    setSelected((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c]));

  const run = async () => {
    setErr(null);
    if (selected.length < 1) {
      setErr("请至少选择 1 个数值特征列");
      return;
    }
    setBusy(true);
    try {
      const r = await postClustering(datasetId, {
        dataset_id: datasetId,
        features: selected,
        auto_k: autoK,
        k: autoK ? null : manualK,
      });
      setRes(r);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h3 className="font-semibold">K-Means 聚类</h3>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input
            type="radio"
            checked={autoK}
            onChange={() => setAutoK(true)}
          />
          自动选 K（肘部 + 轮廓系数）
        </label>
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input
            type="radio"
            checked={!autoK}
            onChange={() => setAutoK(false)}
          />
          手动指定 K
        </label>
        {!autoK && (
          <input
            type="number"
            min={2}
            max={20}
            value={manualK}
            onChange={(e) => setManualK(Number(e.target.value))}
            className="w-16 rounded border border-slate-300 px-2 py-1"
          />
        )}
      </div>

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
            <input
              type="checkbox"
              className="mr-1"
              checked={selected.includes(c)}
              onChange={() => toggle(c)}
            />
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
        {busy ? "计算中…" : "运行聚类"}
      </button>
      {err && <p className="mt-2 text-sm text-red-600">{err}</p>}

      {res && (
        <div className="mt-4 space-y-4">
          {res.data.warning && (
            <p className="rounded bg-amber-50 px-3 py-2 text-xs text-amber-700">
              ⚠ {res.data.warning}
            </p>
          )}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3">
              <div className="flex flex-col">
                <span className="text-[11px] text-slate-500">K（簇数）</span>
                <span className="tabular-nums font-medium text-slate-700">{res.data.k}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[11px] text-slate-500">inertia</span>
                <span className="tabular-nums font-medium text-slate-700">
                  {res.data.inertia.toFixed(4)}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[11px] text-slate-500">轮廓系数</span>
                <span className="tabular-nums font-medium text-slate-700">
                  {res.data.silhouette.toFixed(4)}
                </span>
              </div>
            </div>
          </div>

          <ClusterChart data={res.data} featureNames={selected.slice(0, 2)} />

          <ExplainPanel explanation={res.explanation} />
        </div>
      )}
    </div>
  );
}
