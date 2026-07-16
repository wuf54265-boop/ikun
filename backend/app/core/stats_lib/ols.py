"""OLS 线性回归（自实现）。

核心数学（正规方程 + 手写推断）：
  系数 : β = (XᵀX)⁻¹ Xᵀy        —— 用 np.linalg.solve(XᵀX, Xᵀy) 解正规方程（比显式求逆稳定）
  拟合 : ŷ = Xβ，残差 e = y − ŷ
  残差方差 : σ² = RSS / (n − p)，其中 RSS = eᵀe，p 为参数个数（含截距）
  协方差 : Cov(β) = σ² · (XᵀX)⁻¹
  标准误 : se(βⱼ) = √(σ² · diag((XᵀX)⁻¹)ⱼ)
  t 统计量 : tⱼ = βⱼ / se(βⱼ)
  p 值 : 双尾 t 分布，p = 2·(1 − F_t(|tⱼ|; n−p))，F_t 为 scipy.stats.t 的 CDF
  决定系数 : R² = 1 − RSS/TSS，TSS = Σ(y − ȳ)²
  调整 R² : R²_adj = 1 − (1 − R²)·(n−1)/(n − p)

所有推断（se / t / p）均从 (XᵀX)⁻¹ 与 σ² 手工推导，不调用 statsmodels。
"""
from math import sqrt

import numpy as np
from scipy.stats import t as t_dist


def ols(
    X: np.ndarray,
    y: np.ndarray,
    standardize: bool = False,
    add_intercept: bool = True,
) -> dict:
    """最小二乘线性回归（自实现推断）。

    参数
    ----
    X : (n, d) 自变量矩阵
    y : (n,)   因变量
    standardize : 是否先对 X（不含截距列）和 y 做 z-score 标准化后回归，
                  便于跨量纲比较「标准化系数」/ 特征重要性
    add_intercept : 是否自动在第 0 列插入全 1 截距项

    返回
    ----
    {
      'coefficients': [{'name','coef','std_err','t','p_value'}, ...],
      'r_squared': float,
      'adj_r_squared': float,
      'residuals': ndarray,          # e = y − ŷ
      'fitted': ndarray,             # ŷ
      'residual_std': float,         # √σ²
      'intercept_included': bool,
      'warning': str | None,         # 多重共线性等提示
    }
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n, d = X.shape

    # ① 标准化（z-score），先标准化再决定截距
    if standardize:
        x_std = X.std(axis=0, ddof=0)
        x_std[x_std == 0] = 1.0  # 常数列标准化为 0，不影响回归
        X = (X - X.mean(axis=0)) / x_std
        y_std = y.std()
        y = (y - y.mean()) / (y_std if y_std != 0 else 1.0)

    # ② 自动插入截距项（全 1 列）
    if add_intercept:
        X = np.column_stack([np.ones(n), X])

    n, p = X.shape  # p = 参数个数（含截距）

    # ③ 正规方程：β = (XᵀX)⁻¹ Xᵀy，用 solve 比显式 inv 稳定
    XtX = X.T @ X
    Xty = X.T @ y

    # 数值稳定性：条件数过大说明 XᵀX 接近奇异（多重共线性）
    cond = np.linalg.cond(XtX)
    warning = None
    if cond > 1e10:
        warning = "特征矩阵接近奇异（cond>1e10），可能存在多重共线性，系数估计不稳定"

    try:
        beta = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        # 极端情况退化为伪逆
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        warning = (warning or "") + "；正规方程奇异，已用最小二乘伪逆求解"

    # ④ 拟合与残差
    fitted = X @ beta
    residuals = y - fitted
    rss = float(residuals @ residuals)
    tss = float(((y - y.mean()) ** 2).sum())
    r_squared = 1.0 - rss / tss if tss > 0 else 0.0

    # ⑤ 推断：σ² = RSS/(n−p)，Cov(β) = σ²·(XᵀX)⁻¹
    df_resid = n - p
    sigma2 = rss / df_resid if df_resid > 0 else 0.0
    residual_std = sqrt(sigma2) if sigma2 > 0 else 0.0
    try:
        xtx_inv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        xtx_inv = np.linalg.pinv(XtX)
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.clip(np.diag(cov), 0, None))  # se(βⱼ)

    # t 与双尾 p
    with np.errstate(divide="ignore", invalid="ignore"):
        tvals = np.where(se > 0, beta / se, np.nan)
    if df_resid >= 1:
        pvals = 2.0 * (1.0 - t_dist.cdf(np.abs(tvals), df=df_resid))
        pvals = np.where(np.isnan(tvals), np.nan, pvals)
    else:
        pvals = np.full(p, np.nan)

    # ⑥ 调整 R² = 1 − (1−R²)·(n−1)/(n−p)
    adj_r_squared = (
        1.0 - (1.0 - r_squared) * (n - 1) / df_resid if df_resid > 0 else 0.0
    )

    # ⑦ 组装系数表（name 先占位，服务层再映射真实列名）
    if add_intercept:
        names = ["const"] + [f"x{i}" for i in range(1, d + 1)]
    else:
        names = [f"x{i}" for i in range(1, p + 1)]

    coefficients = []
    for j, name in enumerate(names):
        coefficients.append(
            {
                "name": name,
                "coef": float(beta[j]),
                "std_err": (None if np.isnan(se[j]) else float(se[j])),
                "t": (None if np.isnan(tvals[j]) else float(tvals[j])),
                "p_value": (None if np.isnan(pvals[j]) else float(pvals[j])),
            }
        )

    return {
        "coefficients": coefficients,
        "r_squared": float(r_squared),
        "adj_r_squared": float(adj_r_squared),
        "residuals": residuals,
        "fitted": fitted,
        "residual_std": float(residual_std),
        "intercept_included": bool(add_intercept),
        "warning": warning,
    }
