"""相关性（自实现）：Pearson + 显著性。

r = Σ(xi-x̄)(yi-ȳ) / √(Σ(xi-x̄)²·Σ(yi-ȳ)²)
显著性检验: t = r·√((n-2)/(1-r²)), df = n-2, 双尾 p 值由 t 分布得
"""
import numpy as np
from scipy import stats as _stats


def pearson_with_p(X: np.ndarray) -> dict:
    """输入 X: (n_samples, n_features)，返回:
    {'r': 相关系数矩阵(n×n), 'p_values': p值矩阵(n×n)}。

    设计要点：
    - 核心计算纯 NumPy 手写，不调 scipy.stats.pearsonr。
    - 每对变量「两两剔除 NaN」后用完整观测计算 r。
    - 对角线上 r=1.0, p=0.0。
    - 常数列（std=0）或有效样本 < 3：该格 r=NaN, p=NaN（不崩溃）。
    """
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n, k = X.shape
    r = np.eye(k)               # 对角线 r=1.0
    p = np.zeros((k, k))        # 对角线 p=0.0

    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            xi = X[:, i]
            xj = X[:, j]
            # 逐对剔除 NaN：仅保留两列都非缺失的行
            mask = ~(np.isnan(xi) | np.isnan(xj))
            xi_c = xi[mask]
            xj_c = xj[mask]
            m = xi_c.size
            if m < 3:
                r[i, j] = np.nan
                p[i, j] = np.nan
                continue
            # r = Σ(xi-x̄)(yi-ȳ) / √(Σ(xi-x̄)²·Σ(yi-ȳ)²)
            xm = xi_c - xi_c.mean()
            ym = xj_c - xj_c.mean()
            denom = np.sqrt(np.sum(xm**2) * np.sum(ym**2))
            if denom == 0:  # 常数列（std=0）
                r[i, j] = np.nan
                p[i, j] = np.nan
                continue
            rij = float(np.sum(xm * ym) / denom)
            # 完全相关：t 公式分母 1-r²=0，直接取 p=0
            if abs(rij) >= 1.0 - 1e-12:
                r[i, j] = np.clip(rij, -1.0, 1.0)
                p[i, j] = 0.0
                continue
            # t = r·√((n-2)/(1-r²)), df=n-2, 双尾 p
            t = rij * np.sqrt((m - 2) / (1 - rij**2))
            p[i, j] = float(2 * (1 - _stats.t.cdf(abs(t), df=m - 2)))
            r[i, j] = rij
    return {"r": r, "p_values": p}
