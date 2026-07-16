"""建模服务：回归 / 聚类。"""
import numpy as np
import pandas as pd
from scipy.stats import norm as norm_dist

from app.core.stats_lib import kmeans as lib_km
from app.core.stats_lib import ols as lib_ols
from app.schemas.modeling import (
    ClusteringData,
    ClusteringRequest,
    KCurvePoint,
    RegressionCoeff,
    RegressionData,
    RegressionRequest,
    ResidualPlot,
    ScatterPoint,
)


def _r(v, nd: int = 4):
    """四舍五入到 nd 位；NaN/Inf → None（JSON 安全）。"""
    if v is None:
        return None
    f = float(v)
    if np.isnan(f) or np.isinf(f):
        return None
    return round(f, nd)


def _numeric_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]


def _subsample_idx(n: int, max_n: int, seed: int = 42) -> np.ndarray:
    """均匀子采样索引（用于大样本绘图降载）。"""
    if n <= max_n:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n, size=max_n, replace=False))


def regression(df: pd.DataFrame, body: RegressionRequest) -> RegressionData:
    """OLS 回归：target 为因变量，features 为自变量（默认取所有其余数值列）。"""
    if not body.target:
        raise ValueError("回归需指定 target（因变量）")
    if body.target not in df.columns:
        raise ValueError(f"target 列不存在：{body.target}")
    if not pd.api.types.is_numeric_dtype(df[body.target]):
        raise ValueError(f"target 非数值列：{body.target}")

    all_num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if body.features:
        feats = [c for c in body.features if c in all_num]
        missing = [c for c in body.features if c not in df.columns]
        if missing:
            raise ValueError(f"以下特征列不存在：{missing}")
        non_num = [c for c in body.features if c in df.columns and c not in all_num]
        if non_num:
            raise ValueError(f"以下特征非数值列：{non_num}")
    else:
        feats = [c for c in all_num if c != body.target]
    if not feats:
        raise ValueError("没有可用的数值特征列")

    # 完整观测（逐行剔除含 NaN 的行）
    sub = df[[body.target] + feats].dropna()
    if sub.shape[0] == 0:
        raise ValueError("剔除缺失后无完整观测，无法拟合")
    y = sub[body.target].to_numpy(dtype=float)
    X = sub[feats].to_numpy(dtype=float)
    if X.shape[0] <= X.shape[1]:  # 至少要比参数多 1 个样本
        raise ValueError(
            f"有效样本数({X.shape[0]})不足以拟合（需 > 特征数+截距={X.shape[1] + 1}）"
        )

    res = lib_ols.ols(X, y, standardize=body.standardize)

    # 系数名：const + 真实特征列名（ols 内部用 x1.. 占位）
    coefficients: list[RegressionCoeff] = []
    for i, c in enumerate(res["coefficients"]):
        name = "const" if (i == 0 and res["intercept_included"]) else feats[i - 1]
        coefficients.append(
            RegressionCoeff(
                name=name,
                coef=_r(c["coef"], 6),
                std_err=_r(c["std_err"], 6),
                t=_r(c["t"], 4),
                p_value=_r(c["p_value"], 6),
            )
        )

    # 残差诊断：残差 vs 拟合值（降采样），Q-Q 图（排序残差 vs 理论正态分位）
    residuals = np.asarray(res["residuals"], dtype=float)
    fitted = np.asarray(res["fitted"], dtype=float)
    n = residuals.shape[0]
    plot_idx = _subsample_idx(n, 2000)
    # Q-Q：对残差排序后比对理论分位数
    sorted_res = np.sort(residuals)
    qq_idx = _subsample_idx(n, 2000)
    theoretical = norm_dist.ppf((np.arange(1, n + 1) - 0.5) / n)
    qq_data = [
        {"theoretical": _r(float(theoretical[j]), 4), "sample": _r(float(sorted_res[j]), 4)}
        for j in qq_idx.tolist()
    ]

    return RegressionData(
        coefficients=coefficients,
        r_squared=_r(res["r_squared"], 6),
        adj_r_squared=_r(res["adj_r_squared"], 6),
        residual_plot=ResidualPlot(
            residuals=[_r(float(v), 4) for v in residuals[plot_idx].tolist()],
            fitted=[_r(float(v), 4) for v in fitted[plot_idx].tolist()],
            qq_data=qq_data,
        ),
        warning=res.get("warning"),
    )


def clustering(df: pd.DataFrame, body: ClusteringRequest) -> ClusteringData:
    """K-Means 聚类：features 为特征（默认所有数值列），先 z-score 标准化后聚类。"""
    if body.features:
        feats = _numeric_cols(df, body.features)
        missing = [c for c in body.features if c not in df.columns]
        if missing:
            raise ValueError(f"以下特征列不存在：{missing}")
        non_num = [c for c in body.features if c in df.columns and c not in feats]
        if non_num:
            raise ValueError(f"以下特征非数值列：{non_num}")
    else:
        feats = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(feats) < 1:
        raise ValueError("没有可用的数值特征列")

    sub = df[feats].dropna()
    if sub.shape[0] == 0:
        raise ValueError("剔除缺失后无完整观测，无法聚类")

    # 标准化（z-score）后再聚类
    X = sub[feats].to_numpy(dtype=float)
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    Xz = (X - mean) / std

    k_curve: list[KCurvePoint] = []
    warnings: list[str] = []
    if body.auto_k and body.k is None:
        sel = lib_km.select_k(Xz, k_range=range(2, 11), seed=42)
        for k_i, (inr, sil) in enumerate(zip(sel["inertias"], sel["silhouettes"]), start=2):
            k_curve.append(KCurvePoint(k=k_i, inertia=_r(inr, 4), silhouette=_r(sil, 4)))
        k = sel["best_k"]
        if sel["warning"]:
            warnings.append(sel["warning"])
    else:
        k = body.k if body.k is not None else 3
    if k is None or k < 2:
        k = 3

    res = lib_km.kmeans(Xz, k, seed=42)
    labels = res["labels"]
    silhouette = lib_km.silhouette_score(Xz, labels)
    warnings.extend(res["warnings"])
    sizes = [int((labels == j).sum()) for j in range(k)]

    # 散点图：前两特征（标准化）子采样
    if Xz.shape[1] >= 2:
        s_idx = _subsample_idx(Xz.shape[0], 800)
        scatter = [
            ScatterPoint(
                x=_r(float(Xz[i, 0]), 4),
                y=_r(float(Xz[i, 1]), 4),
                cluster=int(labels[i]),
            )
            for i in s_idx.tolist()
        ]
    else:
        scatter = []

    return ClusteringData(
        k=int(k),
        labels=[int(v) for v in labels.tolist()],
        centroids=[[_r(float(v), 4) for v in row] for row in res["centroids"].tolist()],
        inertia=_r(res["inertia"], 4),
        silhouette=_r(silhouette, 4),
        cluster_sizes=sizes,
        warning="；".join(warnings) if warnings else None,
        k_curve=k_curve,
        scatter=scatter,
    )
