"""数据集上传响应模型。"""
from typing import Any

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    inferred_type: str  # numeric | categorical | datetime | text | boolean
    confidence: float = 0.0
    sample_values: list[Any] = []


class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    cols: int
    columns: list[ColumnInfo] = []
    preview: list[dict] = []  # 前 N 行
    note: str | None = None  # 采样/解析附注（如"已随机采样 N 行"）
