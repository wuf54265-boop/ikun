// 后端 API 封装：统一 base + JSON 解析 + 错误处理
import type {
  AnalysisResponse,
  UploadResponse,
  ProfileResponse,
  CleanRequest,
  CleanData,
  AnomalyRequest,
  AnomalyData,
  CorrelationRequest,
  CorrelationData,
  HypothesisRequest,
  HypothesisData,
  DistributionRequest,
  DistributionData,
  RegressionRequest,
  RegressionData,
  ClusteringRequest,
  ClusteringData,
  InsightRequest,
  InsightData,
  RFMRequest,
  RFMData,
  FunnelRequest,
  FunnelData,
} from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// 文件上传（multipart/form-data）
export async function uploadFile(
  file: File
): Promise<AnalysisResponse<UploadResponse>> {
  const form = new FormData();
  form.append("file", file);
  return request<AnalysisResponse<UploadResponse>>("/datasets/upload", {
    method: "POST",
    body: form,
  });
}

// 带真实上传进度的文件上传（XHR，onProgress 0~100）
export function uploadFileWithProgress(
  file: File,
  onProgress: (pct: number) => void
): Promise<AnalysisResponse<UploadResponse>> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);
    xhr.open("POST", `${BASE}/datasets/upload`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("响应解析失败"));
        }
      } else {
        let detail = `HTTP ${xhr.status}`;
        try {
          const j = JSON.parse(xhr.responseText);
          if (j?.detail) detail = j.detail;
        } catch {
          /* ignore */
        }
        reject(new Error(detail));
      }
    };
    xhr.onerror = () => reject(new Error("网络错误"));
    xhr.send(form);
  });
}

// 数据集画像（用于清洗页获取缺失率 / 数值列 / 箱线图分位数）
export function getProfile(datasetId: string): Promise<AnalysisResponse<ProfileResponse>> {
  return apiGet<AnalysisResponse<ProfileResponse>>(`/datasets/${datasetId}/profile`);
}

// 执行缺失值清洗
export function postClean(
  datasetId: string,
  body: CleanRequest
): Promise<AnalysisResponse<CleanData>> {
  return apiPost<AnalysisResponse<CleanData>>(`/datasets/${datasetId}/clean`, body);
}

// 执行异常检测
export function postAnomalies(
  datasetId: string,
  body: AnomalyRequest
): Promise<AnalysisResponse<AnomalyData>> {
  return apiPost<AnalysisResponse<AnomalyData>>(`/datasets/${datasetId}/anomalies`, body);
}

// 相关性分析
export function postCorrelation(
  datasetId: string,
  body: CorrelationRequest
): Promise<AnalysisResponse<CorrelationData>> {
  return apiPost<AnalysisResponse<CorrelationData>>(`/analysis/correlation`, { ...body, dataset_id: datasetId });
}

// 假设检验
export function postHypothesis(
  datasetId: string,
  body: HypothesisRequest
): Promise<AnalysisResponse<HypothesisData>> {
  return apiPost<AnalysisResponse<HypothesisData>>(`/analysis/hypothesis`, { ...body, dataset_id: datasetId });
}

// 分布检验（KS 正态性）
export function postDistribution(
  datasetId: string,
  body: DistributionRequest
): Promise<AnalysisResponse<DistributionData>> {
  return apiPost<AnalysisResponse<DistributionData>>(`/analysis/distribution`, { ...body, dataset_id: datasetId });
}

// OLS 回归
export function postRegression(
  datasetId: string,
  body: RegressionRequest
): Promise<AnalysisResponse<RegressionData>> {
  return apiPost<AnalysisResponse<RegressionData>>(`/modeling/regression`, { ...body, dataset_id: datasetId });
}

// K-Means 聚类
export function postClustering(
  datasetId: string,
  body: ClusteringRequest
): Promise<AnalysisResponse<ClusteringData>> {
  return apiPost<AnalysisResponse<ClusteringData>>(`/modeling/clustering`, { ...body, dataset_id: datasetId });
}

// AI 报告（非流式，返回完整结构化 JSON）
export function postInsightReport(
  body: InsightRequest
): Promise<AnalysisResponse<InsightData>> {
  return apiPost<AnalysisResponse<InsightData>>(`/insight/report`, body);
}

// 行业模板：RFM 用户分层
export function postRFM(
  datasetId: string,
  body: Omit<RFMRequest, "dataset_id">
): Promise<AnalysisResponse<RFMData>> {
  return apiPost<AnalysisResponse<RFMData>>(`/templates/rfm`, { ...body, dataset_id: datasetId });
}

// 行业模板：漏斗转化
export function postFunnel(
  datasetId: string,
  body: Omit<FunnelRequest, "dataset_id">
): Promise<AnalysisResponse<FunnelData>> {
  return apiPost<AnalysisResponse<FunnelData>>(`/templates/funnel`, { ...body, dataset_id: datasetId });
}

// 内置电商示例数据集（一键体验）
export function postDemoDataset(): Promise<AnalysisResponse<UploadResponse>> {
  return apiPost<AnalysisResponse<UploadResponse>>(`/datasets/demo`, {});
}

// AI 报告（流式 SSE）：逐 chunk 调用 onDelta，结束/失败时 resolve
export async function streamInsightReport(
  body: InsightRequest,
  onDelta: (text: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}/insight/report/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      if (j?.detail) detail = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE 以空行分隔事件
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const evt of events) {
      const line = evt.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (payload === "[DONE]") continue;
      try {
        const obj = JSON.parse(payload);
        if (obj?.text) onDelta(obj.text as string);
      } catch {
        // 非 JSON 兜底：直接当作文本
        onDelta(payload);
      }
    }
  }
}
