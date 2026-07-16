"use client";

import { create } from "zustand";

// 分析结果状态：按步骤 key 缓存各步 AnalysisResponse.data
// 用选择器精准订阅，避免全量重渲染（Context 的痛点在此规避）
interface AnalysisState {
  results: Record<string, unknown>;
  setResult: (key: string, value: unknown) => void;
  reset: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  results: {},
  setResult: (key, value) =>
    set((s) => ({ results: { ...s.results, [key]: value } })),
  reset: () => set({ results: {} }),
}));
