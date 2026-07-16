"use client";

import { useEffect, useState } from "react";

import { AnalysisWizard } from "@/components/AnalysisWizard";
import { AnomalyPanel } from "@/components/AnomalyPanel";
import { MissingValuePanel, type StrategyState } from "@/components/MissingValuePanel";
import { getProfile, postAnomalies, postClean } from "@/lib/api";
import { deriveMissingInfo } from "@/lib/cleaning";
import type {
  AnomalyData,
  AnomalyRequest,
  CleanData,
  FieldProfile,
  MissingStrategyName,
} from "@/lib/types";
import { useDatasetStore } from "@/store/useDatasetStore";
import { useAnalysisStore } from "@/store/useAnalysisStore";

export default function CleanPage({ params }: { params: { id: string } }) {
  const storeId = useDatasetStore((s) => s.datasetId);
  const datasetId = storeId ?? params.id;

  const [fields, setFields] = useState<FieldProfile[]>([]);
  const [rows, setRows] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [strategies, setStrategies] = useState<Record<string, StrategyState>>({});
  const [cleanResult, setCleanResult] = useState<CleanData | null>(null);
  const [cleaning, setCleaning] = useState(false);

  const [anomalyResult, setAnomalyResult] = useState<AnomalyData | null>(null);

  const setResult = useAnalysisStore((s) => s.setResult);

  // 把清洗/异常结果写入全局 store，供「AI 报告」页聚合
  useEffect(() => {
    if (cleanResult || anomalyResult) {
      setResult(`clean-${datasetId}`, {
        data: { clean: cleanResult, anomaly: anomalyResult },
        explanation: {
          interpretation: cleanResult
            ? `数据清洗后行数 ${cleanResult.before_rows} → ${cleanResult.after_rows}，` +
              `改动列：${cleanResult.changed_columns.join("、") || "无"}。`
            : "尚未执行缺失值清洗。",
        },
      });
    }
  }, [cleanResult, anomalyResult, datasetId, setResult]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getProfile(datasetId)
      .then((res) => {
        if (!active) return;
        setFields(res.data.fields);
        setRows(res.data.rows);
        setLoading(false);
      })
      .catch((e) => {
        if (active) {
          setError(String(e));
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [datasetId]);

  const numericColumns = fields
    .filter((f) => f.inferred_type === "numeric")
    .map((f) => f.name);
  const missing = deriveMissingInfo(fields, rows);

  const onStrategyChange = (
    col: string,
    strategy: MissingStrategyName,
    fill?: string
  ) =>
    setStrategies((prev) => ({
      ...prev,
      [col]: { strategy, fill: fill ?? prev[col]?.fill ?? "" },
    }));

  const applyRecommended = () => {
    const next: Record<string, StrategyState> = {};
    for (const m of missing) {
      if (m.recommended === "drop") next[m.column] = { strategy: "drop", fill: "" };
      else if (m.recommended === "median")
        next[m.column] = { strategy: "median", fill: "" };
      else if (m.recommended === "mode") next[m.column] = { strategy: "mode", fill: "" };
      // keep / review 不自动选，交由用户手动决定
    }
    setStrategies(next);
  };

  const runClean = async () => {
    setCleaning(true);
    setError(null);
    try {
      const body = {
        strategies: Object.entries(strategies).map(([column, v]) => ({
          column,
          strategy: v.strategy,
          fill_value: v.fill || null,
        })),
      };
      const res = await postClean(datasetId, body);
      setCleanResult(res.data);
    } catch (e) {
      setError(String(e));
    } finally {
      setCleaning(false);
    }
  };

  const runAnomaly = async (req: AnomalyRequest) => {
    setError(null);
    try {
      const res = await postAnomalies(datasetId, req);
      setAnomalyResult(res.data);
    } catch (e) {
      setError(String(e));
    }
  };

  if (loading) {
    return (
      <div className="flex gap-6">
        <AnalysisWizard datasetId={datasetId} />
        <section className="flex-1 rounded-2xl bg-white p-6 shadow-sm">
          加载数据画像…
        </section>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <AnalysisWizard datasetId={datasetId} />
      <section className="flex-1 space-y-6 rounded-2xl bg-white p-6 shadow-sm">
        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* 缺失值处理区 */}
        <div>
          <h2 className="text-xl font-semibold">数据清洗</h2>
          <p className="mt-1 text-sm text-slate-600">
            缺失值检测与处理建议。策略按列执行，清洗后数据另存为
            <code className="mx-1 rounded bg-slate-100 px-1">_clean.parquet</code>
            ，原始数据不变。
          </p>

          <div className="mt-4">
            <MissingValuePanel
              fields={fields}
              rows={rows}
              strategies={strategies}
              onStrategyChange={onStrategyChange}
            />
          </div>

          <div className="mt-4 flex gap-3">
            <button
              onClick={applyRecommended}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
            >
              一键应用推荐策略
            </button>
            <button
              onClick={runClean}
              disabled={cleaning}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {cleaning ? "清洗中…" : "执行清洗"}
            </button>
          </div>

          {cleanResult && (
            <div className="mt-4 rounded-lg bg-slate-50 p-4 text-sm">
              <div className="font-medium text-slate-700">清洗前后对比</div>
              <div className="mt-2 flex gap-6 tabular-nums text-slate-600">
                <span>
                  行数：{cleanResult.before_rows} →{" "}
                  <span className="font-semibold text-slate-800">
                    {cleanResult.after_rows}
                  </span>
                </span>
                <span>
                  改动列：
                  {cleanResult.changed_columns.length
                    ? cleanResult.changed_columns.join("、")
                    : "无"}
                </span>
              </div>
            </div>
          )}
        </div>

        <hr className="border-slate-100" />

        {/* 异常检测区 */}
        <div>
          <h3 className="text-lg font-semibold">异常检测</h3>
          <p className="mt-1 text-sm text-slate-600">
            IQR / Z-score 为纯 NumPy 自实现；Isolation Forest 调用 sklearn。
          </p>
          <div className="mt-4">
            <AnomalyPanel
              numericColumns={numericColumns}
              fields={fields}
              onDetect={runAnomaly}
              result={anomalyResult}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
