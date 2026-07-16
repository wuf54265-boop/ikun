"""行业模板：RFM / 漏斗。"""
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_dataset_repo
from app.schemas.common import AnalysisResponse
from app.schemas.templates import (
    FunnelData,
    FunnelRequest,
    RFMData,
    RFMRequest,
)
from app.services import templates as tmpl_svc
from app.store.dataset_repo import DatasetRepository

router = APIRouter(prefix="/templates", tags=["templates"])


def _load_analysis_df(repo: DatasetRepository, dataset_id: str):
    """加载用于分析的 DataFrame：优先清洗后版本，否则原始版本。"""
    try:
        return repo.load_clean(dataset_id)
    except FileNotFoundError:
        return repo.load_raw(dataset_id)


@router.post("/rfm", response_model=AnalysisResponse[RFMData])
def rfm(body: RFMRequest, repo: DatasetRepository = Depends(get_dataset_repo)):
    if repo.get_metadata(body.dataset_id) is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = _load_analysis_df(repo, body.dataset_id)
    data = tmpl_svc.rfm(df, body)
    return AnalysisResponse(
        data=data,
        explanation={
            "method": "RFM 用户分层（自实现）",
            "assumptions": [
                "R/F/M 按 20/40/60/80 分位五分位打分(1-5)",
                "R 反向打分：最近购买者得高分（5-分值）；F/M 正向打分（分位序号+1）",
                f"snapshot_date 默认取交易日期最大值（本次={body.snapshot_date or '数据最大日期'}）",
                "按 customer_id 聚合；缺失关键字段的行被剔除",
            ],
            "interpretation": (
                "R=距快照最近购买天数，F=购买次数，M=总金额；"
                "依 R/F/M 分数组合映射 6 类人群（冠军/潜力/忠诚/流失风险/已流失/一般）。"
            ),
            "caveats": [
                "分群规则为经验阈值，可据业务调整",
                "snapshot_date 选择会显著改变 R 与人群分布",
            ],
        },
        meta={
            "method": "rfm",
            "params": {
                "customer_id": body.customer_id,
                "date": body.date,
                "amount": body.amount,
                "snapshot_date": body.snapshot_date,
            },
        },
    )


@router.post("/funnel", response_model=AnalysisResponse[FunnelData])
def funnel(body: FunnelRequest, repo: DatasetRepository = Depends(get_dataset_repo)):
    if repo.get_metadata(body.dataset_id) is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = _load_analysis_df(repo, body.dataset_id)
    data = tmpl_svc.funnel(df, body)
    return AnalysisResponse(
        data=data,
        explanation={
            "method": "漏斗转化率（自实现）",
            "assumptions": [
                "每步统计该列非空且非 0 的行数",
                "conversion 为相对第一步的总体转化率（users_i / users_1 × 100%）",
            ],
            "interpretation": (
                "bottleneck 为相邻两步流失人数最大处，是优先优化的转化断点。"
            ),
            "caveats": ["若某步列全为空/全为 0，users=0，转化率归零"],
        },
        meta={
            "method": "funnel",
            "params": {"steps": body.steps},
        },
    )
