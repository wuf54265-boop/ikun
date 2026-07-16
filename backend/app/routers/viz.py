"""可视化 spec 获取（由 services.visualization 生成 Recharts 配置）。"""
from fastapi import APIRouter

from app.schemas.viz import VizSpec

router = APIRouter(prefix="/viz", tags=["viz"])


@router.get("/{spec_id}", response_model=VizSpec)
def get_viz(spec_id: str):
    # TODO: services.visualization.get_spec(spec_id)
    raise NotImplementedError("services.visualization 待实现")
