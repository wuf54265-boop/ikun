"""可视化 spec（Recharts 兼容）。"""
from pydantic import BaseModel


class VizSpec(BaseModel):
    spec_id: str
    chart_type: str  # heatmap | histogram | boxplot | scatter | funnel | rfm_matrix
    spec: dict = {}  # 前端 ChartRenderer 直接消费的图表配置
