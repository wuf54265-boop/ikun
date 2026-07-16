"""清洗服务：缺失值策略 + 异常检测。

依赖：
- core.stats_lib.anomaly：iqr / zscore（自实现）/ isolation_forest（sklearn 封装）
- store.dataset_repo.DatasetRepository：落盘 _clean.parquet，原始数据不变
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.stats_lib.anomaly import (
    iqr,
    isolation_forest,
    zscore,
)
from app.schemas.cleaning import (
    AnomalyData,
    AnomalyPoint,
    AnomalyRequest,
    CleanData,
    CleanRequest,
)
from app.store.dataset_repo import DatasetRepository

# 推荐策略阈值（与前端 recommend() 保持一致）
HIGH_MISSING_RATE = 0.30  # > 30% 高缺失，建议人工判断
DROP_ROWS_RATE = 0.05  # < 5% 删除含缺失的行


def analyze_missing(df: pd.DataFrame) -> dict:
    """分析每列缺失：数量、缺失率、缺失模式、推荐策略。

    返回 {'rows': int, 'columns': [{column, missing_count, missing_rate,
    missing_pattern, recommended_strategy, dtype}, ...]}

    推荐策略口径：
    - 缺失率 == 0           → keep（无需处理）
    - 缺失率 < 5%           → drop（删除含缺失行）
    - 5% ≤ 缺失率 ≤ 30%     → 数值列 median，类别列 mode
    - 缺失率 > 30%          → review（高缺失警告，建议人工判断，不直接填充）
    缺失模式无法区分 MCAR/MAR，统一标注 "MAR (assumed)"。
    """
    rows = len(df)
    columns_info = []
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        rate = (n_missing / rows) if rows else 0.0
        is_numeric = pd.api.types.is_numeric_dtype(df[col])
        if n_missing == 0:
            recommended = "keep"
            pattern = "complete"
        else:
            pattern = "MAR (assumed)"
            if rate < DROP_ROWS_RATE:
                recommended = "drop"
            elif rate <= HIGH_MISSING_RATE:
                recommended = "median" if is_numeric else "mode"
            else:
                recommended = "review"
        columns_info.append(
            {
                "column": col,
                "missing_count": n_missing,
                "missing_rate": rate,
                "missing_pattern": pattern,
                "recommended_strategy": recommended,
                "dtype": str(df[col].dtype),
            }
        )
    return {"rows": rows, "columns": columns_info}


def apply_missing_strategies(
    df: pd.DataFrame, body: CleanRequest, repo: DatasetRepository, dataset_id: str
) -> CleanData:
    """按用户选择的策略逐列处理缺失值，清洗后落盘 _clean.parquet。

    策略语义：
    - drop  ：删除该列缺失的行
    - mean  ：数值列用均值填充
    - median：数值列用中位数填充；非数值列降级用众数填充
    - mode  ：用众数填充
    - fill  ：用用户指定 fill_value 填充（为空则跳过）
    返回清洗前后对比（changed_columns / before_rows / after_rows）。
    """
    before_rows = len(df)
    df_clean = df.copy()
    changed: list[str] = []

    for s in body.strategies:
        col = s.column
        if col not in df_clean.columns:
            continue
        strat = s.strategy
        if strat == "drop":
            before = len(df_clean)
            df_clean = df_clean[df_clean[col].notna()]
            if len(df_clean) != before:
                changed.append(col)
        elif strat == "mean":
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].fillna(df_clean[col].mean())
                changed.append(col)
        elif strat == "median":
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].fillna(df_clean[col].median())
            else:
                mode_val = (
                    df_clean[col].mode().iloc[0]
                    if not df_clean[col].mode().empty
                    else np.nan
                )
                df_clean[col] = df_clean[col].fillna(mode_val)
            changed.append(col)
        elif strat == "mode":
            mode_val = (
                df_clean[col].mode().iloc[0]
                if not df_clean[col].mode().empty
                else np.nan
            )
            df_clean[col] = df_clean[col].fillna(mode_val)
            changed.append(col)
        elif strat == "fill":
            if s.fill_value is not None:
                df_clean[col] = df_clean[col].fillna(s.fill_value)
                changed.append(col)

    df_clean = df_clean.reset_index(drop=True)
    repo.save_clean(dataset_id, df_clean)
    return CleanData(
        cleaned_dataset_id=dataset_id,
        changed_columns=changed,
        before_rows=before_rows,
        after_rows=len(df_clean),
    )


def detect_anomalies(df: pd.DataFrame, body: AnomalyRequest) -> AnomalyData:
    """根据 method 调用 stats_lib 中的异常检测函数，汇总所有列的异常点。

    - method=iqr / zscore：逐数值列检测（自实现）。
    - method=isolation_forest：多变量检测（sklearn 封装），缺失行先剔除。
    - columns 为空时对所有数值列检测。
    每个 AnomalyPoint：column / index（原始行号）/ value / score。
      IQR 的 score = 超出最近栅栏的 IQR 倍数（≥1 表示至少越界 1 个 IQR）；
      Z-score 的 score = |z|；
      Isolation Forest 的 score = 异常分数（越大越异常），value 记为 NaN。
    """
    method = body.method
    if method not in ("iqr", "zscore", "isolation_forest"):
        raise ValueError(f"不支持的异常检测方法：{method}")

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if body.columns:
        target: list[str] = []
        skipped: list[str] = []
        for c in body.columns:
            if c in numeric_cols:
                target.append(c)
            else:
                skipped.append(c)
        if skipped:
            # 非数值列不参与检测，仅记录（不阻断流程）
            pass
    else:
        target = numeric_cols
        skipped = []

    anomalies: list[AnomalyPoint] = []

    if method == "iqr":
        k = body.threshold if body.threshold is not None else 1.5
        for col in target:
            vals = df[col].to_numpy(dtype=float)
            res = iqr(vals, k=k)
            mask = res["mask"]
            lower, upper, iqr_val = res["lower"], res["upper"], res["IQR"]
            for idx in np.where(mask)[0]:
                idx = int(idx)
                value = float(df[col].iloc[idx])
                if value < lower:
                    score = (lower - value) / iqr_val if iqr_val > 0 else float("inf")
                else:
                    score = (value - upper) / iqr_val if iqr_val > 0 else float("inf")
                anomalies.append(
                    AnomalyPoint(column=col, index=idx, value=value, score=float(score))
                )

    elif method == "zscore":
        threshold = body.threshold if body.threshold is not None else 3.0
        for col in target:
            vals = df[col].to_numpy(dtype=float)
            res = zscore(vals, threshold=threshold)
            mask = res["mask"]
            z = res["z_scores"]
            for idx in np.where(mask)[0]:
                idx = int(idx)
                value = float(df[col].iloc[idx])
                anomalies.append(
                    AnomalyPoint(
                        column=col, index=idx, value=value, score=float(abs(z[idx]))
                    )
                )

    else:  # isolation_forest
        contamination = body.threshold if body.threshold is not None else 0.1
        if not target:
            raise ValueError("Isolation Forest 需要至少 1 个数值列")
        sub = df[target].copy()
        kept_idx = sub.dropna().index.tolist()
        X = sub.loc[kept_idx].to_numpy(dtype=float)
        res = isolation_forest(X, contamination=contamination)
        mask = res["mask"]
        scores = res["scores"]
        col_label = ",".join(target)
        for pos, idx in enumerate(kept_idx):
            if mask[pos]:
                anomalies.append(
                    AnomalyPoint(
                        column=col_label,
                        index=int(idx),
                        value=float("nan"),
                        score=float(scores[pos]),
                    )
                )

    return AnomalyData(method=method, anomaly_count=len(anomalies), anomalies=anomalies)
