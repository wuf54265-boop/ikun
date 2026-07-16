"use client";

import {
  BarChart,
  CartesianGrid,
  LineChart,
  Line,
  Bar,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// 通用图表渲染器：根据后端返回的 spec 选择图表类型
// spec: { chart_type, spec: {...} }
export function ChartRenderer({ spec }: { spec: { chart_type: string; spec: any } }) {
  const { chart_type, spec: data } = spec;

  if (chart_type === "scatter" || chart_type === "cluster") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart>
          <CartesianGrid />
          <XAxis type="number" dataKey="x" />
          <YAxis type="number" dataKey="y" />
          <Tooltip />
          <Scatter data={data.points ?? []} fill="#2563eb" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  if (chart_type === "line" || chart_type === "funnel") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data.series ?? []}>
          <CartesianGrid />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#2563eb" />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  // 默认柱状
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data.series ?? []}>
        <CartesianGrid />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="value" fill="#2563eb" />
      </BarChart>
    </ResponsiveContainer>
  );
}
