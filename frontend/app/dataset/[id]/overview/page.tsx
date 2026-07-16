"use client";

import { useEffect, useState } from "react";

import { AnalysisWizard } from "@/components/AnalysisWizard";
import { apiGet } from "@/lib/api";
import type {
  AnalysisResponse,
  FieldProfile,
  ProfileResponse,
  QualityResponse,
} from "@/lib/types";
import { useAnalysisStore } from "@/store/useAnalysisStore";

const TYPE_LABEL: Record<string, { text: string; cls: string }> = {
  numeric: { text: "数值", cls: "bg-emerald-50 text-emerald-700" },
  categorical: { text: "类别", cls: "bg-amber-50 text-amber-700" },
  datetime: { text: "日期", cls: "bg-violet-50 text-violet-700" },
  boolean: { text: "布尔", cls: "bg-sky-50 text-sky-700" },
  text: { text: "文本", cls: "bg-slate-100 text-slate-600" },
};

// 数据概览页：profile + quality 双请求，渲染字段卡片网格与质量面板
export default function OverviewPage({ params }: { params: { id: string } }) {
  const id = params.id;
  const setResult = useAnalysisStore((s) => s.setResult);

  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [quality, setQuality] = useState<QualityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([
      apiGet<AnalysisResponse<ProfileResponse>>(`/datasets/${id}/profile`),
      apiGet<AnalysisResponse<QualityResponse>>(`/datasets/${id}/quality`),
    ])
      .then(([p, q]) => {
        if (!alive) return;
        setProfile(p.data);
        setQuality(q.data);
        setResult(`profile-${id}`, p.data);
        setResult(`quality-${id}`, q.data);
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [id, setResult]);

  if (loading) {
    return (
      <div className="flex gap-6">
        <AnalysisWizard datasetId={id} />
        <section className="flex-1 rounded-2xl bg-white p-6 shadow-sm text-slate-500">
          加载中…
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex gap-6">
        <AnalysisWizard datasetId={id} />
        <section className="flex-1 rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-red-600">加载失败：{error}</p>
        </section>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <AnalysisWizard datasetId={id} />
      <section className="flex-1 space-y-6">
        <div>
          <h2 className="text-xl font-semibold">数据概览</h2>
          <p className="mt-1 text-sm text-slate-600">
            {profile?.rows.toLocaleString()} 行 × {profile?.cols} 列
          </p>
        </div>

        {quality && <QualityPanel quality={quality} />}

        <div>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">字段字典</h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {profile?.fields.map((f) => (
              <FieldCard key={f.name} field={f} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function FieldCard({ field }: { field: FieldProfile }) {
  const t = TYPE_LABEL[field.inferred_type] ?? TYPE_LABEL.text;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="truncate font-medium text-slate-800" title={field.name}>
          {field.name}
        </span>
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${t.cls}`}>
          {t.text}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
        <span>缺失 {field.missing_rate}%</span>
        <span>·</span>
        <span>唯一值 {field.distinct}</span>
        {field.is_constant && (
          <span className="rounded bg-red-50 px-1.5 py-0.5 text-red-600">常量列</span>
        )}
      </div>

      {field.inferred_type === "numeric" && field.histogram.length > 0 ? (
        <MiniHistogram field={field} />
      ) : field.inferred_type === "categorical" && field.top_values.length > 0 ? (
        <MiniBars
          items={field.top_values.map((v) => ({
            label: v.value,
            value: v.pct ?? 0,
          }))}
        />
      ) : (
        <p className="mt-2 text-xs text-slate-400">
          {field.inferred_type === "numeric"
            ? `均值 ${field.mean ?? "-"} · 中位数 ${field.median ?? "-"}`
            : "无分布预览"}
        </p>
      )}
    </div>
  );
}

// 数值列：用直方图 10 桶做迷你分布图（纯 CSS，无额外依赖）
function MiniHistogram({ field }: { field: FieldProfile }) {
  const max = Math.max(...field.histogram.map((h) => h.count), 1);
  return (
    <div className="mt-3">
      <div className="flex h-12 items-end gap-0.5">
        {field.histogram.map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm bg-blue-500/70"
            style={{ height: `${(h.count / max) * 100}%` }}
            title={`${h.bin_start} ~ ${h.bin_end}: ${h.count}`}
          />
        ))}
      </div>
      <p className="mt-1 text-xs text-slate-400">
        均值 {field.mean ?? "-"} · 中位数 {field.median ?? "-"} · 标准差{" "}
        {field.std ?? "-"}
      </p>
    </div>
  );
}

// 类别列：Top 值占比迷你条
function MiniBars({ items }: { items: { label: string; value: number }[] }) {
  return (
    <div className="mt-3 space-y-1">
      {items.map((it, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="w-24 truncate text-slate-500" title={it.label}>
            {it.label}
          </span>
          <div className="h-2 flex-1 rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-amber-400"
              style={{ width: `${Math.min(100, it.value)}%` }}
            />
          </div>
          <span className="w-10 text-right text-slate-400">{it.value}%</span>
        </div>
      ))}
    </div>
  );
}

// 质量面板：综合评分仪表 + 问题清单
function QualityPanel({ quality }: { quality: QualityResponse }) {
  const score = quality.score;
  const color =
    score >= 80 ? "text-emerald-600" : score >= 60 ? "text-amber-600" : "text-red-600";
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-6">
        <div className="text-center">
          <div className={`text-4xl font-bold ${color}`}>{score}</div>
          <div className="text-xs text-slate-400">综合质量评分</div>
        </div>
        <div className="flex-1">
          <div className="h-2 w-full rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full ${
                score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-amber-500" : "bg-red-500"
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-slate-600">
            重复行 {quality.duplicate_rows.toLocaleString()} · 问题{" "}
            {quality.issues.length} 项
          </p>
        </div>
      </div>

      {quality.issues.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {quality.issues.map((iss, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <span
                className={`mt-0.5 rounded px-1.5 py-0.5 text-xs font-medium ${
                  iss.severity === "error"
                    ? "bg-red-50 text-red-600"
                    : iss.severity === "warning"
                    ? "bg-amber-50 text-amber-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {iss.severity}
              </span>
              <span className="text-slate-600">
                {iss.column && <b className="text-slate-800">{iss.column}：</b>}
                {iss.detail}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
