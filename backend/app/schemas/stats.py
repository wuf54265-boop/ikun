"""统计分析：相关性 / 假设检验 / 分布检验。

注意（Step 5 必要的契约补充，原 prompt schema 漏项）：
- 三个 Request 增加 `dataset_id`：路由需据此加载数据集（原 prompt 的 router 骨架
  `POST /analysis/...` 无 path 参数，dataset_id 只能放 body）。
- `CorrelationData.matrix / p_values` 放宽为 `float | None`：常数列（std=0）相关性
  无定义，pearson_with_p 返回 NaN，需以 null 承载，避免把未定义悄悄变成 0.0。
- `HypothesisData.warning`：卡方期望频数过低 / 自动剔除全零行列时给前端提示。
"""
from pydantic import BaseModel


class CorrelationRequest(BaseModel):
    dataset_id: str
    type: str = "pearson"  # pearson | spearman（本实现仅 pearson）
    columns: list[str] = []


class CorrelationData(BaseModel):
    columns: list[str] = []
    matrix: list[list[float | None]] = []
    p_values: list[list[float | None]] = []


class HypothesisRequest(BaseModel):
    dataset_id: str
    test: str  # welch_t | prop_z | chi2（本实现仅 welch_t / chi2）
    group_column: str | None = None
    value_column: str | None = None
    cont_table: list[list[int]] | None = None  # chi2 用


class HypothesisData(BaseModel):
    test: str
    statistic: float = 0.0
    p_value: float = 0.0
    df: float | None = None
    conclusion: str = ""
    effect_size: float | None = None
    warning: str | None = None


class DistributionRequest(BaseModel):
    dataset_id: str
    test: str  # ks | shapiro（本实现仅 ks）
    column: str


class DistributionData(BaseModel):
    test: str
    statistic: float = 0.0
    p_value: float = 0.0
    is_normal: bool = True
