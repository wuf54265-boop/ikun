"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";

import { AnalysisWizard } from "@/components/AnalysisWizard";
import { getProfile, streamInsightReport } from "@/lib/api";
import { useAnalysisStore } from "@/store/useAnalysisStore";
import { renderMarkdown } from "@/lib/markdown";
import type {
  AnalysisResponse,
  FieldProfile,
  InsightData,
  InsightResultItem,
  ProfileResponse,
} from "@/lib/types";

const MODULES = [
  { key: "overview", label: "数据概览" },
  { key: "clean", label: "数据清洗" },
  { key: "stats", label: "统计分析" },
  { key: "model", label: "建模分析" },
] as const;

type ModuleKey = (typeof MODULES)[number]["key"];

export default function ReportPage({ params }: { params: { id: string } }) {
  const datasetId = params.id;

  const [fields, setFields] = useState<FieldProfile[]>([]);
  const [rows, setRows] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [tone, setTone] = useState<"professional" | "casual">("professional");
  const [selected, setSelected] = useState<ModuleKey[]>([
    "overview",
    "clean",
    "stats",
    "model",
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveText, setLiveText] = useState("");
  const [report, setReport] = useState<InsightData | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [missing, setMissing] = useState<string[]>([]);

  // 加载画像以获取行/列数（dataset_context）
  useEffect(() => {
    let active = true;
    getProfile(datasetId)
      .then((res: AnalysisResponse<ProfileResponse>) => {
        if (!active) return;
        setFields(res.data.fields);
        setRows(res.data.rows);
      })
      .catch((e) => {
        if (active) setLoadError(String(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [datasetId]);

  const cols = useMemo(() => fields.length, [fields]);

  const toggle = (k: ModuleKey) =>
    setSelected((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));

  // 从全局 store 聚合前序结果；返回 {results, missing}
  function collect(): { results: InsightResultItem[]; missing: string[] } {
    const all = useAnalysisStore.getState().results as Record<string, any>;
    const results: InsightResultItem[] = [];
    const miss: string[] = [];

    if (selected.includes("overview")) {
      const profile = all[`profile-${datasetId}`];
      const quality = all[`quality-${datasetId}`];
      if (profile || quality) {
        results.push({
          module: "数据概览",
          data: { profile, quality },
          explanation: { interpretation: quality?.summary ?? "" },
        });
      } else miss.push("数据概览");
    }
    if (selected.includes("clean")) {
      const c = all[`clean-${datasetId}`];
      if (c) results.push({ module: "数据清洗", data: c.data, explanation: c.explanation });
      else miss.push("数据清洗");
    }
    if (selected.includes("stats")) {
      const map: [string, string][] = [
        ["stats-corr", "相关性分析"],
        ["stats-hyp", "假设检验"],
        ["stats-dist", "分布检验"],
      ];
      let any = false;
      for (const [k, label] of map) {
        const it = all[`${k}-${datasetId}`];
        if (it) {
          results.push({ module: label, data: it.data, explanation: it.explanation });
          any = true;
        }
      }
      if (!any) miss.push("统计分析");
    }
    if (selected.includes("model")) {
      const map: [string, string][] = [
        ["model-reg", "回归分析"],
        ["model-cluster", "聚类分析"],
      ];
      let any = false;
      for (const [k, label] of map) {
        const it = all[`${k}-${datasetId}`];
        if (it) {
          results.push({ module: label, data: it.data, explanation: it.explanation });
          any = true;
        }
      }
      if (!any) miss.push("建模分析");
    }
    return { results, missing: miss };
  }

  const generate = async () => {
    setError(null);
    setReport(null);
    setDegraded(false);
    setLiveText("");

    if (selected.length === 0) {
      setError("请至少选择一个分析模块");
      return;
    }
    const { results, missing: miss } = collect();
    setMissing(miss);
    if (results.length === 0) {
      setError("暂无可聚合的分析结果。请先到各分析页运行分析（数据概览会自动加载）。");
      return;
    }

    const body = {
      results,
      tone,
      dataset_context: { rows, cols },
    };

    setBusy(true);
    let acc = ""; // 本地累加，避免依赖闭包中的 liveText（异步 setState 不更新）
    try {
      await streamInsightReport(body, (t) => {
        acc += t;
        setLiveText((prev) => prev + t);
      });
      // 流结束后解析累积文本为结构化 JSON
      setReport(parseStreamed(acc));
    } catch (e) {
      // API 不可用（如未配置 key / 网络错误）：用前序 explanation 拼降级摘要
      const fallback = buildDegraded(results);
      setReport(fallback);
      setDegraded(true);
      setError(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex gap-6">
      <AnalysisWizard datasetId={datasetId} />
      <section className="flex-1 space-y-6 rounded-2xl bg-white p-6 shadow-sm">
        <div>
          <h2 className="text-xl font-semibold">AI 分析报告</h2>
          <p className="mt-1 text-sm text-slate-600">
            LLM 仅「翻译」前序结构化计算结果，所有数字来自你的统计输出，不编造。
          </p>
          {loading && <p className="mt-2 text-sm text-slate-400">加载数据画像…</p>}
          {!loading && loadError && (
            <div className="mt-3 rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700">
              数据画像加载失败：{loadError}
            </div>
          )}
        </div>

        {/* 配置区 */}
        <div className="rounded-xl border border-slate-200 p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="text-sm text-slate-600">语气：</div>
            {(["professional", "casual"] as const).map((t) => (
              <label key={t} className="flex items-center gap-1 text-sm">
                <input
                  type="radio"
                  checked={tone === t}
                  onChange={() => setTone(t)}
                />
                {t === "professional" ? "专业" : "通俗"}
              </label>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-600">包含模块：</span>
            {MODULES.map((m) => (
              <label
                key={m.key}
                className={`cursor-pointer rounded-full border px-3 py-1 text-xs ${
                  selected.includes(m.key)
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-slate-300 text-slate-600"
                }`}
              >
                <input
                  type="checkbox"
                  className="mr-1"
                  checked={selected.includes(m.key)}
                  onChange={() => toggle(m.key)}
                />
                {m.label}
              </label>
            ))}
          </div>
          <button
            onClick={generate}
            disabled={busy}
            className="mt-4 rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? "生成中…" : "生成报告"}
          </button>
        </div>

        {missing.length > 0 && (
          <div className="rounded-lg bg-amber-50 px-4 py-2 text-xs text-amber-700">
            以下所选模块尚未运行，未纳入报告：{missing.join("、")}。请先到对应页面分析。
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {degraded && (
          <div className="rounded-lg bg-amber-50 px-4 py-2 text-xs text-amber-700">
            ⚠ LLM 服务暂不可用，已用各模块结构化解读拼成降级摘要。配置 OPENAI_API_KEY
            后可生成完整自然语言报告。
          </div>
        )}

        {/* 流式打字机 / 最终报告 */}
        {busy && liveText && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
            <div
              className="prose-sm max-w-none whitespace-pre-wrap"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(liveText) }}
            />
            <p className="mt-2 text-xs text-slate-400">生成中…</p>
          </div>
        )}

        {!busy && report && (
          <ReportView report={report} datasetId={datasetId} />
        )}
      </section>
    </div>
  );
}

/* ----------------- 报告展示 ----------------- */
function ReportView({
  report,
  datasetId,
}: {
  report: InsightData;
  datasetId: string;
}) {
  return (
    <div className="space-y-5">
      <div>
        <h3 className="font-semibold">摘要</h3>
        <div
          className="mt-2 text-sm leading-relaxed text-slate-700"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(report.summary) }}
        />
      </div>

      <Section title="关键发现">
        <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
          {report.key_findings.map((f, i) => (
            <li key={i}>
              <Finding text={f} datasetId={datasetId} />
            </li>
          ))}
        </ol>
      </Section>

      <Section title="行动建议">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {report.suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </Section>

      <Section title="风险提示">
        <ul className="list-disc space-y-1 pl-5 text-sm text-red-700">
          {report.risks.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h3 className="mb-2 font-semibold">{title}</h3>
      {children}
    </div>
  );
}

/* 关键发现：解析前置 [来源标签] 并渲染为可跳转的彩色标签 */
function Finding({ text, datasetId }: { text: string; datasetId: string }) {
  const m = text.match(/^\[([^\]]+)\]\s*([\s\S]*)$/);
  if (!m) return <span>{text}</span>;
  const tag = m[1];
  const rest = m[2];
  const { module, color } = classify(tag);
  return (
    <span>
      <Link
        href={`/dataset/${datasetId}/${module}`}
        className={`mr-2 rounded-full border px-2 py-0.5 text-[11px] ${color}`}
      >
        [{tag}]
      </Link>
      {rest}
    </span>
  );
}

function classify(tag: string): { module: ModuleKey | "report"; color: string } {
  const t = tag.toLowerCase();
  if (/概览|画像|背景|质量/.test(t))
    return { module: "overview", color: "border-blue-200 bg-blue-50 text-blue-700" };
  if (/清洗|缺失|异常/.test(t))
    return { module: "clean", color: "border-amber-200 bg-amber-50 text-amber-700" };
  if (/相关/.test(t))
    return { module: "stats", color: "border-green-200 bg-green-50 text-green-700" };
  if (/检验|假设|t检验|卡方|分布|ks|正态/.test(t))
    return { module: "stats", color: "border-green-200 bg-green-50 text-green-700" };
  if (/回归|ols/.test(t))
    return { module: "model", color: "border-purple-200 bg-purple-50 text-purple-700" };
  if (/聚类|k-?means/.test(t))
    return { module: "model", color: "border-purple-200 bg-purple-50 text-purple-700" };
  return { module: "report", color: "border-slate-200 bg-slate-50 text-slate-600" };
}

/* ----------------- 工具函数 ----------------- */
function parseStreamed(text: string): InsightData {
  let s = text.trim();
  if (s.startsWith("```")) {
    s = s.replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim();
  }
  try {
    const obj = JSON.parse(s);
    return {
      summary: String(obj.summary ?? ""),
      key_findings: Array.isArray(obj.key_findings) ? obj.key_findings.map(String) : [],
      suggestions: Array.isArray(obj.suggestions) ? obj.suggestions.map(String) : [],
      risks: Array.isArray(obj.risks) ? obj.risks.map(String) : [],
    };
  } catch {
    // 解析失败：把累积文本当作纯摘要
    return { summary: text, key_findings: [], suggestions: [], risks: [] };
  }
}

function buildDegraded(results: InsightResultItem[]): InsightData {
  const findings: string[] = [];
  for (const r of results) {
    const interp = r.explanation?.interpretation;
    if (interp) findings.push(`【${r.module}】${interp}`);
  }
  return {
    summary: "LLM 服务暂不可用，以下是结构化分析摘要：\n" + findings.join("\n"),
    key_findings: findings,
    suggestions: [],
    risks: [],
  };
}
