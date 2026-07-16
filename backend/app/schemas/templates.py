"""行业模板：RFM / 漏斗。"""
from pydantic import BaseModel


class RFMRequest(BaseModel):
    dataset_id: str
    customer_id: str
    date: str
    amount: str
    snapshot_date: str | None = None


class RFMSegment(BaseModel):
    segment: str
    count: int = 0
    share: float = 0.0


class RFMData(BaseModel):
    segments: list[RFMSegment] = []
    matrix: list[dict] = []
    suggestions: list[str] = []


class FunnelRequest(BaseModel):
    dataset_id: str
    steps: list[str]


class FunnelStep(BaseModel):
    step: str
    users: int = 0
    conversion: float = 0.0  # 相对上一步转化率


class FunnelData(BaseModel):
    steps: list[FunnelStep] = []
    bottleneck: str | None = None  # 流失最大的相邻步骤（"步骤A→步骤B"）
