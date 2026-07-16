"""行业模板服务：RFM / 漏斗。"""
from app.core.stats_lib import funnel as funnel_lib
from app.core.stats_lib import rfm as rfm_lib
from app.schemas.templates import (
    FunnelData,
    FunnelRequest,
    RFMData,
    RFMRequest,
)


def rfm(df, body: RFMRequest) -> RFMData:
    """RFM 用户分层：调用自实现引擎，组装 RFMData。"""
    out = rfm_lib.rfm_analysis(
        df, body.customer_id, body.date, body.amount, body.snapshot_date
    )
    return RFMData(**out)


def funnel(df, body: FunnelRequest) -> FunnelData:
    """漏斗转化：调用自实现引擎，组装 FunnelData。"""
    out = funnel_lib.funnel_analysis(df, body.steps)
    return FunnelData(**out)
