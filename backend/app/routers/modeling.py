"""建模分析：回归 / 聚类。"""
from fastapi import APIRouter, Depends

from app.dependencies import get_dataset_repo
from app.schemas.common import AnalysisResponse
from app.schemas.modeling import (
    ClusteringData,
    ClusteringRequest,
    RegressionData,
    RegressionRequest,
)
from app.services import modeling as modeling_service
from app.store.dataset_repo import DatasetRepository

router = APIRouter(prefix="/modeling", tags=["modeling"])


def _load_analysis_df(repo: DatasetRepository, dataset_id: str):
    """加载用于分析的 DataFrame：优先清洗后版本，否则原始版本。"""
    try:
        return repo.load_clean(dataset_id)
    except FileNotFoundError:
        return repo.load_raw(dataset_id)


@router.post("/regression", response_model=AnalysisResponse[RegressionData])
def regression(body: RegressionRequest, repo: DatasetRepository = Depends(get_dataset_repo)):
    df = _load_analysis_df(repo, body.dataset_id)
    data = modeling_service.regression(df, body)
    exp = {
        "method": "OLS 线性回归（正规方程自实现）",
        "assumptions": [
            "线性关系：y ≈ Xβ + ε",
            "误差项独立、同方差、近似正态",
            "自变量非完全共线（否则 (XᵀX) 奇异，系数无唯一解）",
        ],
        "interpretation": (
            "系数 β 由正规方程 β=(XᵀX)⁻¹Xᵀy 解得（np.linalg.solve，比显式求逆稳定）。"
            "标准误 se(βⱼ)=√(σ²·diag((XᵀX)⁻¹)ⱼ)，σ²=RSS/(n−p)，"
            "t=βⱼ/se(βⱼ)，双尾 p 来自 t 分布。R²=1−RSS/TSS，调整R²惩罚过拟合特征。"
        ),
        "caveats": [
            "本实现自推导所有推断，未调用 statsmodels（statsmodels 仅用于测试对照）",
            "p<0.05 表示该系数在统计上显著异于 0",
        ]
        + ([data.warning] if data.warning else []),
    }
    return AnalysisResponse(
        data=data,
        explanation=exp,
        meta={"method": "ols", "params": body.model_dump(exclude={"dataset_id"})},
    )


@router.post("/clustering", response_model=AnalysisResponse[ClusteringData])
def clustering(body: ClusteringRequest, repo: DatasetRepository = Depends(get_dataset_repo)):
    df = _load_analysis_df(repo, body.dataset_id)
    data = modeling_service.clustering(df, body)
    exp = {
        "method": "K-Means 聚类（k-means++ 初始化自实现）",
        "assumptions": [
            "簇呈近似球形、大小相近",
            "特征已标准化（z-score），避免量纲主导距离",
            "使用欧氏距离",
        ],
        "interpretation": (
            "质心用 k-means++ 初始化（按距离平方概率选，提升收敛与稳定性）；"
            "迭代分配最近质心→更新为簇均值至收敛。选 K 用肘部(inertia)+轮廓系数"
            "(自实现，不调 sklearn)。silhouette 越接近 1 聚类越分明。"
        ),
        "caveats": [
            "K-Means 对初始质心敏感，本实现固定 seed=42 保证可复现",
            "轮廓系数 / k-means++ 均自实现，sklearn 仅用于测试对照",
        ]
        + ([data.warning] if data.warning else []),
    }
    return AnalysisResponse(
        data=data,
        explanation=exp,
        meta={"method": "kmeans", "params": body.model_dump(exclude={"dataset_id"})},
    )
