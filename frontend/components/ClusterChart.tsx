"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { ClusteringData } from "@/lib/types";

const CLUSTER_COLORS = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#d97706",
  "#7c3aed",
  "#0891b2",
  "#db2777",
  "#65a30d",
  "#9333ea",
  "#0d9488",
];

/** 聚类可视化：肘部图 + 轮廓系数图 + 散点图（前两特征，质心标星）+ 各簇规模。 */
export function ClusterChart({
  data,
  featureNames,
}: {
  data: ClusteringData;
  featureNames: string[];
}) {
  const xName = featureNames[0] ?? "特征1";
  const yName = featureNames[1] ?? "特征2";

  // 散点按簇拆分（每簇一个 Scatter series 以便着色）
  const perCluster: Record<number, { x: number; y: number; cluster: number }[]> = {};
  data.scatter.forEach((p) => {
    (perCluster[p.cluster] ||= []).push(p);
  });
  const clusters = Object.keys(perCluster)
    .map(Number)
    .sort((a, b) => a - b);

  // 质心（取前两维，标准化空间）
  const centroidPts = data.centroids.map((c, i) => ({
    x: c[0] ?? 0,
    y: c[1] ?? 0,
    cluster: i,
  }));

  const sizesData = data.cluster_sizes.map((s, i) => ({ name: `簇${i}`, size: s }));

  return (
    <div className="space-y-6">
      {data.k_curve.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-3">
            <h4 className="mb-2 text-sm font-medium">肘部图（K vs inertia）</h4>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.k_curve}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="k" type="number" />
                  <YAxis />
                  <Tooltip />
                  <Line dataKey="inertia" stroke="#2563eb" dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 p-3">
            <h4 className="mb-2 text-sm font-medium">轮廓系数（K vs silhouette）</h4>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.k_curve}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="k" type="number" />
                  <YAxis />
                  <Tooltip />
                  <Line dataKey="silhouette" stroke="#16a34a" dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-slate-200 p-3">
        <h4 className="mb-2 text-sm font-medium">
          聚类散点图（{xName} vs {yName}，标准化后）
        </h4>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="x" name={xName} />
              <YAxis type="number" dataKey="y" name={yName} />
              <ZAxis range={[60, 60]} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              {clusters.map((c) => (
                <Scatter
                  key={c}
                  name={`簇${c}`}
                  data={perCluster[c]}
                  fill={CLUSTER_COLORS[c % CLUSTER_COLORS.length]}
                />
              ))}
              <Scatter name="质心" data={centroidPts} shape="star" fill="#111827" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 p-3">
        <h4 className="mb-2 text-sm font-medium">各簇规模</h4>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sizesData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="size">
                {sizesData.map((_, i) => (
                  <Cell key={i} fill={CLUSTER_COLORS[i % CLUSTER_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
