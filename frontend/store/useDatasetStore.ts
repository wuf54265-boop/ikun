"use client";

import { create } from "zustand";

// 会话级数据集状态：跨页面共享当前 dataset_id / 文件名
// 注意：只存轻量元数据，原始 DataFrame 始终在后端（Parquet 存储层）
interface DatasetState {
  datasetId: string | null;
  filename: string | null;
  setDataset: (id: string, filename?: string) => void;
  clear: () => void;
}

export const useDatasetStore = create<DatasetState>((set) => ({
  datasetId: null,
  filename: null,
  setDataset: (id, filename) => set({ datasetId: id, filename: filename ?? null }),
  clear: () => set({ datasetId: null, filename: null }),
}));
