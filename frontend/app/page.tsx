"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { postDemoDataset } from "@/lib/api";

// 落地页（首页）
export default function HomePage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const startDemo = async () => {
    setBusy(true);
    setErr(null);
    try {
      const res = await postDemoDataset();
      const id = res.data.dataset_id;
      router.push(`/dataset/${id}/overview`);
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  };

  return (
    <div className="space-y-10">
      <section className="rounded-2xl bg-white p-10 shadow-sm">
        <h1 className="text-3xl font-bold">AI 数据分析助手</h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          上传一份表格，即可获得统计建模结果 + 自然语言洞察 + 可视化报告。
          核心统计方法透明、可查、可复现，AI 只做「翻译」不做「黑盒结论」。
        </p>
        <div className="mt-6 flex gap-3">
          <a
            href="/upload"
            className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700"
          >
            上传数据
          </a>
          <a
            href="/methods"
            className="rounded-lg border border-slate-300 px-5 py-2.5 font-medium hover:bg-slate-100"
          >
            算法与方法
          </a>
        </div>
      </section>

      <section className="rounded-2xl bg-gradient-to-r from-blue-50 to-indigo-50 p-8 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">体验 Demo</h2>
            <p className="mt-1 max-w-xl text-sm text-slate-600">
              无需上传，一键生成内置电商示例数据（约 500 行，含客户/日期/金额/品类等），
              直接体验 RFM 用户分层、转化漏斗等模板。
            </p>
          </div>
          <button
            onClick={startDemo}
            disabled={busy}
            className="shrink-0 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? "生成中…" : "一键体验 Demo"}
          </button>
        </div>
        {err && <p className="mt-3 text-sm text-red-700">{err}</p>}
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          ["统计硬实力", "OLS / K-Means / 假设检验 / 分布检验等核心算法自实现"],
          ["行业模板", "RFM 用户分层、转化漏斗等电商高频分析开箱即用"],
          ["全过程可解释", "每个结论标注方法 / 假设 / 解读，点击展开公式"],
        ].map(([t, d]) => (
          <div key={t} className="rounded-xl bg-white p-5 shadow-sm">
            <h3 className="font-semibold">{t}</h3>
            <p className="mt-2 text-sm text-slate-600">{d}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
