"use client";

import { useEffect } from "react";
import Link from "next/link";

// Next.js 路由级错误边界：捕获子路由渲染期未预期错误
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // 生产环境可在此上报到监控（Sentry 等）
    console.error("页面渲染错误：", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-5xl font-bold text-red-300">⚠️</p>
      <h1 className="mt-4 text-2xl font-semibold text-slate-800">出错了</h1>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        页面渲染时发生了意外错误。可点击下方按钮重试；若持续出现，请返回首页重新操作。
      </p>
      {error?.message && (
        <pre className="mt-4 max-w-lg overflow-x-auto rounded bg-slate-900 p-3 text-left text-xs text-slate-300">
          {error.message}
        </pre>
      )}
      <div className="mt-8 flex gap-3">
        <button
          onClick={reset}
          className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          重试
        </button>
        <Link
          href="/"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
