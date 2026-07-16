// 与后端 schemas 对齐的 TS 类型

export interface Explanation {
  method: string;
  assumptions: string[];
  interpretation: string;
  caveats: string[];
}

export interface Meta {
  method: string;
  params: Record<string, unknown>;
}

export interface AnalysisResponse<T> {
  data: T;
  explanation: Explanation;
  meta: Meta;
}

// 数据集
export interface ColumnInfo {
  name: string;
  inferred_type: string;
  confidence: number;
  sample_values: unknown[];
}
export interface UploadResponse {
  dataset_id: string;
  filename: string;
  rows: number;
  cols: number;
  columns: ColumnInfo[];
  preview: Record<string, unknown>[];
  note?: string | null;
}

// 数据理解（profiling）
export interface TopValue {
  value: string;
  count: number;
  pct?: number | null;
}
export interface HistBin {
  bin_start?: number | null;
  bin_end?: number | null;
  count: number;
}
export interface FieldProfile {
  name: string;
  dtype: string;
  inferred_type: string;
  confidence: number;
  missing_rate: number;
  distinct: number;
  is_constant: boolean;
  mean?: number | null;
  median?: number | null;
  std?: number | null;
  min?: number | null;
  max?: number | null;
  q1?: number | null;
  q3?: number | null;
  skewness?: number | null;
  kurtosis?: number | null;
  histogram: HistBin[];
  top_values: TopValue[];
}
export interface ProfileResponse {
  dataset_id: string;
  rows: number;
  cols: number;
  fields: FieldProfile[];
}
export interface QualityIssue {
  type: string;
  column?: string | null;
  detail: string;
  severity: string; // info | warning | error
}
export interface QualityResponse {
  dataset_id: string;
  score: number;
  duplicate_rows: number;
  issues: QualityIssue[];
}

// 数据清洗
export type MissingStrategyName = "drop" | "mean" | "median" | "mode" | "fill";
export interface MissingStrategy {
  column: string;
  strategy: MissingStrategyName;
  fill_value?: unknown | null;
}
export interface CleanRequest {
  strategies: MissingStrategy[];
}
export interface CleanData {
  cleaned_dataset_id: string;
  changed_columns: string[];
  before_rows: number;
  after_rows: number;
}

export type AnomalyMethod = "iqr" | "zscore" | "isolation_forest";
export interface AnomalyRequest {
  method: AnomalyMethod;
  columns?: string[];
  threshold?: number | null; // 按 method 复用：iqr→k，zscore→threshold，isolation_forest→contamination
}
export interface AnomalyPoint {
  column: string;
  index: number;
  value: number | null;
  score: number | null;
}
export interface AnomalyData {
  method: string;
  anomaly_count: number;
  anomalies: AnomalyPoint[];
}

// 统计分析
export interface CorrelationRequest {
  dataset_id: string;
  type?: string; // pearson（本实现仅 pearson）
  columns: string[];
}
export interface CorrelationData {
  columns: string[];
  matrix: (number | null)[][];
  p_values: (number | null)[][];
}
export interface HypothesisRequest {
  dataset_id: string;
  test: "welch_t" | "chi2";
  group_column?: string | null;
  value_column?: string | null;
  cont_table?: number[][] | null;
}
export interface HypothesisData {
  test: string;
  statistic: number;
  p_value: number;
  df: number | null;
  conclusion: string;
  effect_size: number | null;
  warning?: string | null;
}
export interface DistributionRequest {
  dataset_id: string;
  test: "ks";
  column: string;
}
export interface DistributionData {
  test: string;
  statistic: number;
  p_value: number;
  is_normal: boolean;
}

// 建模分析
export interface RegressionCoeff {
  name: string;
  coef: number;
  std_err: number | null;
  t: number | null;
  p_value: number | null;
}
export interface QQPoint {
  theoretical: number;
  sample: number;
}
export interface ResidualPlot {
  residuals: number[];
  fitted: number[];
  qq_data: QQPoint[];
}
export interface RegressionRequest {
  dataset_id: string;
  target: string;
  features: string[];
  standardize?: boolean;
}
export interface RegressionData {
  coefficients: RegressionCoeff[];
  r_squared: number;
  adj_r_squared: number;
  residual_plot: ResidualPlot;
  warning?: string | null;
}

export interface KCurvePoint {
  k: number;
  inertia: number;
  silhouette: number;
}
export interface ScatterPoint {
  x: number;
  y: number;
  cluster: number;
}
export interface ClusteringRequest {
  dataset_id: string;
  features: string[];
  k?: number | null;
  auto_k?: boolean;
}
export interface ClusteringData {
  k: number;
  labels: number[];
  centroids: number[][];
  inertia: number;
  silhouette: number;
  cluster_sizes: number[];
  warning?: string | null;
  k_curve: KCurvePoint[];
  scatter: ScatterPoint[];
}

/* ----------------- AI 分析报告 ----------------- */
export interface InsightResultItem {
  module: string;
  data: unknown;
  explanation?: { interpretation?: string };
}

export interface InsightRequest {
  results: InsightResultItem[];
  tone: "professional" | "casual";
  dataset_context?: { rows?: number; cols?: number } | null;
}

export interface InsightData {
  summary: string;
  key_findings: string[];
  suggestions: string[];
  risks: string[];
}

/* ----------------- 行业模板：RFM / 漏斗 ----------------- */
export interface RFMRequest {
  dataset_id: string;
  customer_id: string;
  date: string;
  amount: string;
  snapshot_date?: string | null;
}
export interface RFMSegment {
  segment: string;
  count: number;
  share: number;
}
export interface RFMMatrixRow {
  customer_id: string;
  R: number;
  F: number;
  M: number;
  score_r: number;
  score_f: number;
  score_m: number;
  segment: string;
}
export interface RFMData {
  segments: RFMSegment[];
  matrix: RFMMatrixRow[];
  suggestions: string[];
}

export interface FunnelRequest {
  dataset_id: string;
  steps: string[];
}
export interface FunnelStep {
  step: string;
  users: number;
  conversion: number;
}
export interface FunnelData {
  steps: FunnelStep[];
  bottleneck: string | null;
}
