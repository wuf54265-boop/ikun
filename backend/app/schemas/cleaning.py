"""数据清洗：缺失值策略 + 异常检测。"""
from typing import Any

from pydantic import BaseModel


class MissingStrategy(BaseModel):
    column: str
    strategy: str  # drop | mean | median | mode | fill
    fill_value: Any | None = None


class CleanRequest(BaseModel):
    strategies: list[MissingStrategy] = []


class CleanData(BaseModel):
    cleaned_dataset_id: str
    changed_columns: list[str] = []
    before_rows: int = 0
    after_rows: int = 0


class AnomalyRequest(BaseModel):
    method: str  # iqr | zscore | isolation_forest
    columns: list[str] = []
    threshold: float | None = None


class AnomalyPoint(BaseModel):
    column: str
    index: int
    value: float
    score: float | None = None


class AnomalyData(BaseModel):
    method: str
    anomaly_count: int = 0
    anomalies: list[AnomalyPoint] = []
