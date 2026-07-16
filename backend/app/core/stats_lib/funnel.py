"""漏斗转化率（自实现，行业模板）。

按步骤顺序计算各步人数与总体转化率，定位流失最大的相邻两步。
公式：
  users_i   = 该步列非空且非 0 的行数
  conv_i    = users_i / users_1 × 100%   （相对第一步的总体转化率）
  bottleneck = argmax_i (users_{i-1} - users_i)  （相邻两步流失人数最大处）
"""
import pandas as pd


def funnel_analysis(df: pd.DataFrame, steps: list[str]) -> dict:
    """返回 steps(人数+总体转化率%) 与 bottleneck(流失最大的相邻步)。"""
    rows: list[dict] = []
    first_users: int | None = None
    for step in steps:
        if step not in df.columns:
            users = 0
        else:
            col = df[step]
            # 非空 且 非 0 视为"到达该步"
            users = int(((col.notna()) & (col != 0)).sum())
        if first_users is None:
            first_users = users
        conv = (users / first_users * 100.0) if first_users else 0.0
        rows.append({"step": step, "users": users, "conversion": round(conv, 2)})

    bottleneck: str | None = None
    max_drop = 0
    for i in range(1, len(rows)):
        drop = rows[i - 1]["users"] - rows[i]["users"]
        if drop > max_drop:
            max_drop = drop
            bottleneck = f"{rows[i - 1]['step']}→{rows[i]['step']}"

    return {"steps": rows, "bottleneck": bottleneck}
