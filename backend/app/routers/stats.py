"""统计分析：相关性 / 假设检验 / 分布检验。"""
from fastapi import APIRouter, Depends

from app.dependencies import get_dataset_repo
from app.schemas.common import AnalysisResponse
from app.schemas.stats import (
    CorrelationData,
    CorrelationRequest,
    DistributionData,
    DistributionRequest,
    HypothesisData,
    HypothesisRequest,
)
from app.services import stats as stats_service
from app.store.dataset_repo import DatasetRepository

router = APIRouter(prefix="/analysis", tags=["stats"])


def _load_analysis_df(repo: DatasetRepository, dataset_id: str):
    """加载用于分析的 DataFrame：优先清洗后版本，否则原始版本。"""
    try:
        return repo.load_clean(dataset_id)
    except FileNotFoundError:
        return repo.load_raw(dataset_id)


@router.post("/correlation", response_model=AnalysisResponse[CorrelationData])
def correlation(body: CorrelationRequest, repo: DatasetRepository = Depends(get_dataset_repo)):
    df = _load_analysis_df(repo, body.dataset_id)
    data = stats_service.correlation(df, body)
    return AnalysisResponse(
        data=data,
        explanation={
            "method": "Pearson 积差相关（自实现）",
            "assumptions": [
                "两变量近似双变量正态",
                "线性关系",
                "每对变量按完整观测（两两剔除缺失）计算",
            ],
            "interpretation": "r∈[-1,1]，绝对值越大线性相关越强；对角线 r=1。",
            "caveats": [
                "相关系数≠因果",
                "对异常值敏感；常数列（std=0）相关性无定义，矩阵中以 null 表示",
            ],
        },
        meta={"method": "pearson_with_p", "params": {"columns": body.columns}},
    )


@router.post("/hypothesis", response_model=AnalysisResponse[HypothesisData])
def hypothesis(body: HypothesisRequest, repo: DatasetRepository = Depends(get_dataset_repo)):
    df = _load_analysis_df(repo, body.dataset_id)
    data = stats_service.hypothesis(df, body)
    if body.test == "welch_t":
        exp = {
            "method": "Welch t 检验（自实现）",
            "assumptions": [
                "两组独立",
                "组内近似正态（大样本下放宽）",
                "不要求方差齐性（故用 Welch 而非 Student t）",
            ],
            "interpretation": (
                "原假设 H₀：两组均值相等。t=(x̄₁-x̄₂)/√(s₁²/n₁+s₂²/n₂)，"
                "自由度用 Welch–Satterthwaite 公式，双尾 p。Cohen's d 为效应量。"
            ),
            "caveats": ["两组方差均为 0 且均值不同则检验无定义"]
            + ([data.warning] if data.warning else []),
        }
    else:  # chi2
        exp = {
            "method": "卡方独立性检验（自实现）",
            "assumptions": [
                "观测独立",
                "期望频数足够大（见 warning）",
            ],
            "interpretation": (
                "原假设 H₀：两变量独立。χ²=Σ(O-E)²/E，E=行和×列和/N，"
                "df=(r-1)(c-1)。Cramér's V 为关联强度效应量。"
            ),
            "caveats": ["期望频数过低时结论不可靠，建议 Fisher 精确检验"]
            + ([data.warning] if data.warning else []),
        }
    return AnalysisResponse(
        data=data,
        explanation=exp,
        meta={"method": body.test, "params": body.model_dump(exclude={"dataset_id"})},
    )


@router.post("/distribution", response_model=AnalysisResponse[DistributionData])
def distribution(body: DistributionRequest, repo: DatasetRepository = Depends(get_dataset_repo)):
    df = _load_analysis_df(repo, body.dataset_id)
    data = stats_service.distribution(df, body)
    return AnalysisResponse(
        data=data,
        explanation={
            "method": "KS 正态性检验（Lilliefors 修正，自实现）",
            "assumptions": [
                "H₀：数据服从正态分布",
                "均值与标准差由样本估计（故用 Lilliefors 而非标准 KS 临界值）",
            ],
            "interpretation": (
                "D=max|F_n(x)-Φ((x-x̄)/s)|；α=0.05 临界值 n>50 用 0.886/√n，"
                "n≤50 查 Lilliefors 表。D<临界值则视为正态。"
            ),
            "caveats": [
                "p 值为基于 Kolmogorov 分布的大样本近似（Lilliefors 更严格，仅参考）",
                "小样本（n<5）或常数序列结论不可靠",
            ],
        },
        meta={"method": "ks_normality", "params": {"column": body.column}},
    )
