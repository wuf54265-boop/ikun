"use client";

import { useRef, useState } from "react";

const ACCEPT = ".csv,.xlsx,.xls";

// 拖拽 / 点击上传区域：负责文件选择与校验，把合法文件通过 onFile 抛出
export function FileDropzone({
  onFile,
  maxMb = 50,
  error,
}: {
  onFile: (file: File) => void;
  maxMb?: number;
  error?: string | null;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  function validate(file: File | undefined) {
    if (!file) return;
    const okExt = file.name.toLowerCase().match(/\.(csv|xlsx|xls)$/);
    if (!okExt) {
      setLocalError("仅支持 .csv / .xlsx / .xls 文件");
      return;
    }
    if (file.size > maxMb * 1024 * 1024) {
      setLocalError(`文件 ${ (file.size / 1024 / 1024).toFixed(1) }MB 超过 ${maxMb}MB 上限`);
      return;
    }
    setLocalError(null);
    onFile(file);
  }

  const shownError = error ?? localError;

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          validate(e.dataTransfer.files?.[0]);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition ${
          dragOver ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50"
        }`}
      >
        <p className="text-base font-medium text-slate-700">
          拖拽文件到此处，或点击选择
        </p>
        <p className="mt-1 text-sm text-slate-500">
          支持 CSV / Excel，单文件 ≤ {maxMb}MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => validate(e.target.files?.[0])}
        />
      </div>
      {shownError && (
        <p className="mt-2 text-sm text-red-600">{shownError}</p>
      )}
    </div>
  );
}
