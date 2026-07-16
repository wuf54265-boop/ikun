"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DataPreview } from "@/components/DataPreview";
import { FileDropzone } from "@/components/FileDropzone";
import { uploadFileWithProgress } from "@/lib/api";
import type { UploadResponse } from "@/lib/types";
import { useDatasetStore } from "@/store/useDatasetStore";

const MAX_MB = 50;

// 上传页：拖拽/选择 → 校验 → 带进度上传 → 展示预览 → 跳转概览
export default function UploadPage() {
  const router = useRouter();
  const setDataset = useDatasetStore((s) => s.setDataset);

  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setProgress(0);
    try {
      const res = await uploadFileWithProgress(file, setProgress);
      const data: UploadResponse = res.data;
      setResult(data);
      setDataset(data.dataset_id, data.filename);
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-white p-8 shadow-sm">
        <h2 className="text-xl font-semibold">上传数据</h2>
        <p className="mt-2 text-sm text-slate-600">
          支持 CSV / Excel，单文件 ≤ {MAX_MB}MB。上传后自动完成类型推断与落盘。
        </p>

        <div className="mt-5">
          <FileDropzone
            onFile={(f) => {
              setFile(f);
              setResult(null);
              setError(null);
            }}
            maxMb={MAX_MB}
            error={error ?? undefined}
          />
        </div>

        {file && (
          <div className="mt-4 flex items-center gap-3">
            <span className="text-sm text-slate-600">
              已选择：<span className="font-medium">{file.name}</span>（
              {(file.size / 1024 / 1024).toFixed(2)} MB）
            </span>
            <button
              onClick={handleUpload}
              disabled={loading}
              className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white disabled:opacity-50"
            >
              {loading ? `上传中 ${progress}%` : "上传并分析"}
            </button>
          </div>
        )}

        {loading && (
          <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full bg-blue-600 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </section>

      {result && (
        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <Metric label="行数" value={result.rows.toLocaleString()} />
            <Metric label="列数" value={result.cols.toLocaleString()} />
            <Metric label="字段类型" value={`${result.columns.length} 列`} />
          </div>

          {result.note && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
              {result.note}
            </p>
          )}

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-700">
              字段类型
            </h3>
            <div className="flex flex-wrap gap-2">
              {result.columns.map((c) => (
                <span
                  key={c.name}
                  className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
                >
                  {c.name}
                  <span className="ml-1 font-medium text-blue-600">
                    {c.inferred_type}
                  </span>
                </span>
              ))}
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-700">
              数据预览（前 {result.preview.length} 行）
            </h3>
            <DataPreview columns={result.columns} preview={result.preview} />
          </div>

          <div className="pt-2">
            <button
              onClick={() => router.push(`/dataset/${result.dataset_id}/overview`)}
              className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700"
            >
              下一步：数据概览 →
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold text-slate-800">{value}</div>
    </div>
  );
}
