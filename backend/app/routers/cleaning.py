"""数据清洗：缺失值处理 / 异常检测。"""
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_dataset_repo
from app.schemas.cleaning import (
    AnomalyData,
    AnomalyRequest,
    CleanData,
    CleanRequest,
)
from app.schemas.common import AnalysisResponse, Explanation, Meta
from app.services import cleaning as cleaning_svc
from app.store.dataset_repo import DatasetRepository

router = APIRouter(tags=["cleaning"])

# AnomalyRequest 仅含 method/columns/threshold 三个字段；
# 按 method 复用 threshold 承载方法专属参数：iqr→k，zscore→threshold，isolation_forest→contamination
_METHOD_DEFAULTS = {"iqr": 1.5, "zscore": 3.0, "isolation_forest": 0.1}
_METHOD_PARAM_LABEL = {
    "iqr": "k",
    "zscore": "threshold",
    "isolation_forest": "contamination",
}
_METHOD_FORMULA = {
    "iqr": "异常 if x < Q1 - k·IQR 或 x > Q3 + k·IQR（IQR = Q3 - Q1）",
    "zscore": "z = (x-μ)/σ，|z| > threshold 判异常（纯 NumPy 自实现）",
    "isolation_forest": "Isolation Forest（sklearn 封装）：基于随机划分路径长度，异常点路径更短，分数越低越异常",
}


@router.post(
    "/datasets/{dataset_id}/clean", response_model=AnalysisResponse[CleanData]
)
def clean(
    dataset_id: str,
    body: CleanRequest,
    repo: DatasetRepository = Depends(get_dataset_repo),
):
    if repo.get_metadata(dataset_id) is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = repo.load_raw(dataset_id)
    result = cleaning_svc.apply_missing_strategies(df, body, repo, dataset_id)
    strategy_desc = (
        [f"{s.column}:{s.strategy}" for s in body.strategies]
        or ["(未提交策略，仅完成落盘，数据与原文件一致)"]
    )
    return AnalysisResponse[CleanData](
        data=result,
        explanation=Explanation(
            method="缺失值处理",
            assumptions=[
                "drop=删除该列缺失的行；mean/median 仅用于数值列；mode=类别列众数；fill=自定义值",
                "清洗后数据另存为 _clean.parquet，原始数据保持不变（可追溯）",
            ],
            interpretation=(
                f"应用策略 {strategy_desc}；清洗后 {result.after_rows} 行"
                f"（原 {result.before_rows} 行）；改动列：{result.changed_columns or '无'}"
            ),
            caveats=["若未提交任何策略，清洗后数据与原始一致，仅完成落盘动作"],
        ),
        meta=Meta(method="missing_imputation", params={"strategies": strategy_desc}),
    )


@router.post(
    "/datasets/{dataset_id}/anomalies", response_model=AnalysisResponse[AnomalyData]
)
def anomalies(
    dataset_id: str,
    body: AnomalyRequest,
    repo: DatasetRepository = Depends(get_dataset_repo),
):
    if repo.get_metadata(dataset_id) is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    # 优先用清洗后版本（若有），否则用原始数据
    try:
        df = repo.load_clean(dataset_id)
    except Exception:
        df = repo.load_raw(dataset_id)

    try:
        result = cleaning_svc.detect_anomalies(df, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    param_label = _METHOD_PARAM_LABEL[body.method]
    param_val = body.threshold if body.threshold is not None else _METHOD_DEFAULTS[body.method]
    return AnalysisResponse[AnomalyData](
        data=result,
        explanation=Explanation(
            method=f"异常检测（{body.method}）",
            assumptions=[
                "仅对数值列检测；未指定 columns 时对所有数值列检测",
                "NaN 不参与异常判定（iqr/zscore：对应位置记为非异常）",
            ],
            interpretation=(
                f"方法 {body.method}，共检出 {result.anomaly_count} 个异常点；"
                f"参数 {param_label}={param_val}"
            ),
            caveats=[
                _METHOD_FORMULA[body.method],
                "Isolation Forest 为集成模型，单点解释性弱于 IQR/Z-score",
            ],
        ),
        meta=Meta(
            method=body.method,
            params={
                "columns": body.columns or "all_numeric",
                param_label: param_val,
            },
        ),
    )
