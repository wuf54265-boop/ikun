"""自动数据理解：字段画像 + 数据质量报告。

复用 utils.column_types.infer_column_type 保证类型口径与接入层一致。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from app.schemas.profiling import (
    FieldProfile,
    HistBin,
    ProfileResponse,
    QualityIssue,
    QualityResponse,
    TopValue,
)
from app.utils.column_types import infer_column_type


def _round(x: float | None, n: int = 4) -> float | None:
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, n)


def _numeric_profile(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return {}
    counts, edges = np.histogram(s, bins=10)
    hist = [
        HistBin(
            bin_start=_round(edges[i]),
            bin_end=_round(edges[i + 1]),
            count=int(counts[i]),
        )
        for i in range(len(counts))
    ]
    return {
        "mean": _round(s.mean()),
        "median": _round(s.median()),
        "std": _round(s.std()),
        "min": _round(s.min()),
        "max": _round(s.max()),
        "q1": _round(s.quantile(0.25)),
        "q3": _round(s.quantile(0.75)),
        "skewness": _round(s.skew()),
        "kurtosis": _round(s.kurtosis()),
        "histogram": hist,
    }


def _categorical_profile(series: pd.Series) -> dict:
    s = series.dropna()
    total = len(s)
    if total == 0:
        return {}
    vc = s.value_counts().head(5)
    top = [
        TopValue(value=str(k), count=int(v), pct=_round(v / total * 100, 2))
        for k, v in vc.items()
    ]
    return {"top_values": top}


def column_profile(series: pd.Series, name: str) -> FieldProfile:
    inferred, confidence = infer_column_type(series)
    missing_rate = float(series.isna().mean() * 100)
    distinct = int(series.nunique(dropna=True))
    base: dict = {
        "name": str(name),
        "dtype": str(series.dtype),
        "inferred_type": inferred,
        "confidence": round(float(confidence), 3),
        "missing_rate": _round(missing_rate, 2),
        "distinct": distinct,
        "is_constant": distinct <= 1,
    }
    if inferred == "numeric":
        base.update(_numeric_profile(series))
    else:
        base.update(_categorical_profile(series))
    return FieldProfile(**base)


def profile_dataset(df: pd.DataFrame, dataset_id: str) -> ProfileResponse:
    """逐列画像，返回 ProfileResponse。"""
    fields = [column_profile(df[c], c) for c in df.columns]
    return ProfileResponse(
        dataset_id=dataset_id,
        rows=int(len(df)),
        cols=int(df.shape[1]),
        fields=fields,
    )


def _quality_score(df: pd.DataFrame, issues: list[QualityIssue], dup: int) -> float:
    """综合质量评分（0~100）。

    起始 100，逐类扣分：
    - 每列缺失率 ×10（缺失越多扣越多）
    - 重复行占比 ×20
    - 每个常量列 -5
    """
    score = 100.0
    n = len(df)
    for c in df.columns:
        score -= df[c].isna().mean() * 10
    if n > 0:
        score -= (dup / n) * 20
    for iss in issues:
        if iss.type == "constant":
            score -= 5
    return max(0.0, min(100.0, score))


def quality_report(df: pd.DataFrame, dataset_id: str) -> QualityResponse:
    """数据质量报告：缺失 / 重复 / 常量 / 高基数 ID 检测 + 综合评分。"""
    issues: list[QualityIssue] = []
    n = len(df)

    # 缺失
    for c in df.columns:
        mr = df[c].isna().mean()
        if mr > 0:
            severity = "warning" if mr > 0.3 else "info"
            issues.append(
                QualityIssue(
                    type="missing",
                    column=str(c),
                    detail=f"缺失率 {mr * 100:.1f}%",
                    severity=severity,
                )
            )

    # 重复行
    dup = int(df.duplicated().sum())
    if dup > 0:
        issues.append(
            QualityIssue(
                type="duplicate",
                column=None,
                detail=f"存在 {dup} 行完全重复（占比 {dup / n * 100:.1f}%）",
                severity="warning" if dup / max(n, 1) > 0.05 else "info",
            )
        )

    # 常量列
    for c in df.columns:
        if df[c].nunique(dropna=True) <= 1:
            issues.append(
                QualityIssue(
                    type="constant",
                    column=str(c),
                    detail="该列仅有一个唯一值，可能无分析价值",
                    severity="warning",
                )
            )

    # 高基数 ID 提示
    for c in df.columns:
        if n > 0 and df[c].nunique(dropna=True) == n:
            issues.append(
                QualityIssue(
                    type="high_cardinality_id",
                    column=str(c),
                    detail="唯一值数 = 行数，疑似主键 / ID 列",
                    severity="info",
                )
            )

    score = _quality_score(df, issues, dup)
    return QualityResponse(
        dataset_id=dataset_id,
        score=round(score, 1),
        duplicate_rows=dup,
        issues=issues,
    )
