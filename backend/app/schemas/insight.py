"""AI 分析报告：汇总结构化结果 -> 自然语言。"""
from pydantic import BaseModel


class InsightRequest(BaseModel):
    results: list[dict] = []  # 前序各步 AnalysisResponse 的 data 聚合
    tone: str = "professional"  # professional | casual
    # 数据集背景（行/列数），用于注入 prompt；前端从画像结果提取后传入
    dataset_context: dict | None = None  # {"rows": int, "cols": int}


class InsightData(BaseModel):
    summary: str = ""
    key_findings: list[str] = []
    suggestions: list[str] = []
    risks: list[str] = []
