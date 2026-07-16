"""统一响应信封：data(结果) + explanation(方法/假设/解读) + meta(参数)。

可解释性设计核心（见产品规划 2.5）：每个分析都返回这三件套，前端可展开公式。
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Explanation(BaseModel):
    method: str = ""
    assumptions: list[str] = []
    interpretation: str = ""
    caveats: list[str] = []


class Meta(BaseModel):
    method: str = ""
    params: dict = {}


class AnalysisResponse(BaseModel, Generic[T]):
    data: T
    explanation: Explanation = Explanation()
    meta: Meta = Meta()
