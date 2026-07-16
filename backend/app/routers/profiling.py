"""自动数据理解：字段画像 / 质量报告。"""
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_dataset_repo
from app.schemas.common import AnalysisResponse, Explanation
from app.schemas.profiling import ProfileResponse, QualityResponse
from app.services.profiling import profile_dataset, quality_report
from app.store.dataset_repo import DatasetRepository

router = APIRouter(tags=["profiling"])


@router.get(
    "/datasets/{dataset_id}/profile",
    response_model=AnalysisResponse[ProfileResponse],
)
def profile(dataset_id: str, repo: DatasetRepository = Depends(get_dataset_repo)):
    if repo.get_metadata(dataset_id) is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    df = repo.load_raw(dataset_id)
    result = profile_dataset(df, dataset_id)
    return AnalysisResponse(
        data=result,
        explanation=Explanation(
            method="逐列类型推断 + 描述统计",
            interpretation=(
                "numeric 列给出均值/中位数/分位数/偏度/峰度与直方图；"
                "categorical 列给出 Top5 值与占比；datetime/text/boolean 列给出唯一值数。"
            ),
            caveats=[
                "超大文件基于上传时的采样子集统计（见上传响应 note）",
                "偏度/峰度在样本量较小时不稳定",
            ],
        ),
        meta={"rows": result.rows, "cols": result.cols},
    )


@router.get(
    "/datasets/{dataset_id}/quality",
    response_model=AnalysisResponse[QualityResponse],
)
def quality(dataset_id: str, repo: DatasetRepository = Depends(get_dataset_repo)):
    if repo.get_metadata(dataset_id) is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    df = repo.load_raw(dataset_id)
    result = quality_report(df, dataset_id)
    return AnalysisResponse(
        data=result,
        explanation=Explanation(
            method="缺失率 + 重复行 + 常量列 + 高基数ID 检测，加权扣分得到 0-100 综合评分",
            assumptions=[
                "综合评分起始 100；缺失每列扣 缺失率×10，重复行扣 占比×20，常量列每列 -5",
            ],
            interpretation=f"当前综合质量评分 {result.score}，共 {len(result.issues)} 项问题。",
        ),
        meta={"score": result.score},
    )
