"""数据理解：字段画像 + 数据质量报告。

模型命名遵循 Step 3 指令：ProfileResponse / QualityResponse（对外信封内 data 的类型）。
"""
from typing import Any

from pydantic import BaseModel


class TopValue(BaseModel):
    value: str
    count: int
    pct: float | None = None  # 占比 %


class HistBin(BaseModel):
    bin_start: float | None = None
    bin_end: float | None = None
    count: int


class FieldProfile(BaseModel):
    name: str
    dtype: str
    inferred_type: str  # numeric | categorical | datetime | text | boolean
    confidence: float = 0.0
    missing_rate: float = 0.0  # 缺失率（%，0~100）
    distinct: int = 0
    is_constant: bool = False
    # 数值型统计
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    q1: float | None = None
    q3: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None
    histogram: list[HistBin] = []
    # 类别型
    top_values: list[TopValue] = []


class ProfileResponse(BaseModel):
    dataset_id: str
    rows: int
    cols: int
    fields: list[FieldProfile] = []


class QualityIssue(BaseModel):
    type: str  # missing | duplicate | constant | high_cardinality_id | ...
    column: str | None = None
    detail: str = ""
    severity: str = "info"  # info | warning | error


class QualityResponse(BaseModel):
    dataset_id: str
    score: float = 0.0  # 综合质量评分 0~100
    duplicate_rows: int = 0
    issues: list[QualityIssue] = []
