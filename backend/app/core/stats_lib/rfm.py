"""RFM 引擎（自实现，行业模板）。

由交易表聚合 R(最近距今天数)/F(次数)/M(金额)，五分位打分(1-5)，
RFM 组合映射分群标签（冠军/忠诚/流失风险/已流失…）。
公式：
  R = (snapshot_date - 最近购买日期).days
  F = 购买次数
  M = 总金额
  五分位打分：cut = quantile([0.2,0.4,0.6,0.8])；score = searchsorted(cut, x)+1（F/M 越大分越高；R 反向）
"""
import numpy as np
import pandas as pd


def _quintile_score(series: pd.Series, reverse: bool = False) -> np.ndarray:
    """按 20/40/60/80 分位点把连续值映射为 1-5 的整数分。

    reverse=True 时用于 R：值越小分越高（最近购买的得高分）。
    """
    q = series.quantile([0.2, 0.4, 0.6, 0.8]).to_numpy()
    idx = np.searchsorted(q, series.to_numpy(), side="right")  # 0..4
    return (5 - idx) if reverse else (idx + 1)


def _segment(r: int, f: int, m: int) -> str:
    """按 RFM 分数组合分群（规则见产品规划/Step8 prompt）。"""
    if r >= 4 and f >= 4 and m >= 4:
        return "冠军客户"
    if r >= 4 and f < 3 and m >= 3:
        return "潜力客户"
    if r < 3 and f >= 4 and m >= 4:
        return "忠诚客户"
    if r < 3 and f < 3 and m >= 3:
        return "流失风险"
    if r < 3 and f < 3 and m < 3:
        return "已流失"
    return "一般客户"


_SUGGESTIONS = {
    "冠军客户": "高价值高活跃：优先维护，提供 VIP 权益、专属客服与新品内测，最大化留存与复购。",
    "潜力客户": "近期活跃但购买少：用首单券/会员首充引导提升购买频次，培养为忠诚客户。",
    "忠诚客户": "曾高频高消费但近期沉寂：用召回券、唤醒邮件与个性化推荐拉回，防止流失。",
    "流失风险": "消费金额尚可但频次与活跃双低：加强触达频率，做交叉推荐与限时活动刺激。",
    "已流失": "低频低额且沉寂：低成本批量召回（短信/EDM），评估 ROI，不投入高价资源。",
    "一般客户": "处于中间层：用分层运营与常规促销逐步提升其 RFM 任一维度。",
}

_ALL_SEGMENTS = ["冠军客户", "潜力客户", "忠诚客户", "流失风险", "已流失", "一般客户"]


def rfm_analysis(
    df: pd.DataFrame,
    customer_id: str,
    date: str,
    amount: str,
    snapshot_date=None,
) -> dict:
    """返回 segments / matrix / suggestions。

    - segments: 各分群人数与占比（含空群，count=0）
    - matrix: 每客户 R/F/M 原始值与 score，按 M 降序取 top 500（防数据过大）
    - suggestions: 运营建议文本（每个出现的分群一条）
    """
    work = df[[customer_id, date, amount]].copy()
    work[date] = pd.to_datetime(work[date], errors="coerce")
    work[amount] = pd.to_numeric(work[amount], errors="coerce")
    work = work.dropna(subset=[customer_id, date, amount])
    if work.empty:
        return {"segments": [], "matrix": [], "suggestions": []}

    snap = pd.to_datetime(snapshot_date) if snapshot_date else work[date].max()

    agg = (
        work.groupby(customer_id)
        .agg(
            R=(date, lambda s: int((snap - s.max()).days)),
            F=(date, "count"),
            M=(amount, "sum"),
        )
        .reset_index()
    )

    agg["score_r"] = _quintile_score(agg["R"], reverse=True)
    agg["score_f"] = _quintile_score(agg["F"])
    agg["score_m"] = _quintile_score(agg["M"])
    agg["segment"] = [
        _segment(r, f, m)
        for r, f, m in zip(agg["score_r"], agg["score_f"], agg["score_m"])
    ]

    total = len(agg)
    seg_counts = agg["segment"].value_counts().to_dict()
    segments = [
        {
            "segment": name,
            "count": int(seg_counts.get(name, 0)),
            "share": round(seg_counts.get(name, 0) / total, 4) if total else 0.0,
        }
        for name in _ALL_SEGMENTS
    ]

    matrix = (
        agg.sort_values("M", ascending=False)
        .head(500)[
            [customer_id, "R", "F", "M", "score_r", "score_f", "score_m", "segment"]
        ]
        .rename(columns={customer_id: "customer_id"})
        .to_dict("records")
    )
    # numpy int -> python int，保证 JSON 可序列化
    for row in matrix:
        for k, v in row.items():
            if isinstance(v, (np.integer,)):
                row[k] = int(v)
            elif isinstance(v, (np.floating,)):
                row[k] = float(v)

    present = [s for s in _ALL_SEGMENTS if seg_counts.get(s, 0) > 0]
    suggestions = [_SUGGESTIONS[s] for s in present]

    return {"segments": segments, "matrix": matrix, "suggestions": suggestions}
