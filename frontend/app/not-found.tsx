import Link from "next/link";

// 友好 404 页：路由未匹配时由 Next.js 自动渲染
export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-bold text-slate-300">404</p>
      <h1 className="mt-4 text-2xl font-semibold text-slate-800">页面走丢了</h1>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        你访问的地址不存在，或数据集已被清理。先回到首页上传一份数据，或体验一键 Demo。
      </p>
      <div className="mt-8 flex gap-3">
        <Link
          href="/"
          className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          返回首页
        </Link>
        <Link
          href="/upload"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          上传数据
        </Link>
      </div>
    </div>
  );
}
