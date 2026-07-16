"""可视化服务：生成 Recharts 兼容 spec。"""
from app.schemas.viz import VizSpec


def get_spec(spec_id: str) -> VizSpec:
    # TODO: 根据 spec_id 返回对应图表配置（热力图/分布/聚类散点/RFM矩阵/漏斗）
    raise NotImplementedError("visualization 待实现")
