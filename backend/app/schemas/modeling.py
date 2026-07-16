"""建模分析：回归 / 聚类。

Schema 契约（Step 6）：
- Request 增加 `dataset_id`：路由据此加载数据集（与 stats 模块一致，dataset_id 放 body，
  因 router 无 path 参数）。reference: schemas/stats.py 的 Step 5 做法。
- `RegressionData.residual_plot` 由裸 dict 改为具体结构 ResidualPlot（residuals / fitted /
  qq_data），便于前端直接喂 Recharts。
- `ClusteringData` 扩展：`warning`（共线性弱/空簇等）、`k_curve`（auto_k 时返回各 K 的
  inertia+silhouette，供肘部图/轮廓系数图）、`scatter`（前两特征标准化后的子采样点，供散点图）。
  这些扩展不与 prompt 冲突，仅为支撑前端可视化。
"""
from pydantic import BaseModel


class RegressionRequest(BaseModel):
    dataset_id: str
    target: str
    features: list[str] = []
    standardize: bool = False


class RegressionCoeff(BaseModel):
    name: str
    coef: float
    std_err: float | None = None
    t: float | None = None
    p_value: float | None = None


class QQPoint(BaseModel):
    theoretical: float
    sample: float


class ResidualPlot(BaseModel):
    residuals: list[float] = []
    fitted: list[float] = []
    qq_data: list[QQPoint] = []


class RegressionData(BaseModel):
    coefficients: list[RegressionCoeff] = []
    r_squared: float = 0.0
    adj_r_squared: float = 0.0
    residual_plot: ResidualPlot = ResidualPlot()
    warning: str | None = None


class ClusteringRequest(BaseModel):
    dataset_id: str
    features: list[str] = []
    k: int | None = None
    auto_k: bool = True


class KCurvePoint(BaseModel):
    k: int
    inertia: float
    silhouette: float


class ScatterPoint(BaseModel):
    x: float
    y: float
    cluster: int


class ClusteringData(BaseModel):
    k: int
    labels: list[int] = []
    centroids: list[list[float]] = []
    inertia: float = 0.0
    silhouette: float = 0.0
    cluster_sizes: list[int] = []
    warning: str | None = None
    k_curve: list[KCurvePoint] = []  # auto_k 时返回各 K 的探索结果
    scatter: list[ScatterPoint] = []  # 前两特征（标准化）子采样点，供散点图
