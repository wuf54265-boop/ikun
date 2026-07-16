import "./globals.css";
import type { Metadata } from "next";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "AI 数据分析助手",
  description: "可解释的 AI 数据分析助手 · 统计建模 + 自然语言洞察 + 可视化",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <Nav />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
