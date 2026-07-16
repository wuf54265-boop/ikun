import Link from "next/link";

// 顶部导航
export function Nav() {
  return (
    <header className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-lg font-bold text-blue-600">
          AI 数据分析助手
        </Link>
        <nav className="flex gap-4 text-sm text-slate-600">
          <Link href="/upload" className="hover:text-blue-600">
            上传
          </Link>
          <Link href="/methods" className="hover:text-blue-600">
            算法与方法
          </Link>
        </nav>
      </div>
    </header>
  );
}
