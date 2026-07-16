"""异常检测。

- iqr / zscore：自实现（纯 NumPy，不依赖 sklearn / scipy）。
- isolation_forest：调用 sklearn（工程取舍，见产品规划 6.2，不自实现）。

设计约束（见产品规划 2.5 / Step 4 技术约束）：
1. iqr / zscore 只 import numpy，入参 np.ndarray，出参 dict，纯函数。
2. NaN 安全：计算统计量时忽略 NaN；返回的 mask 中 NaN 位置记为 False（不算异常）。
3. isolation_forest 中 X 不应含 NaN，调用方负责预处理。
"""
from __future__ import annotations

import numpy as np


def iqr(x: np.ndarray, k: float = 1.5) -> dict:
    """IQR 法：异常 if x < Q1 - k·IQR or x > Q3 + k·IQR，其中 IQR = Q3 - Q1（默认 k=1.5）。

    返回 {'mask': bool数组, 'lower': 下界, 'upper': 上界, 'Q1': Q1, 'Q3': Q3, 'IQR': IQR}
    mask 中 NaN 位置恒为 False。
    """
    arr = np.asarray(x, dtype=float)
    nan_mask = np.isnan(arr)
    clean = arr[~nan_mask]
    if clean.size == 0:
        return {
            "mask": nan_mask.copy(),
            "lower": float("nan"),
            "upper": float("nan"),
            "Q1": float("nan"),
            "Q3": float("nan"),
            "IQR": float("nan"),
        }
    q1, q3 = np.percentile(clean, [25, 75])
    iqr_val = q3 - q1
    lower = q1 - k * iqr_val
    upper = q3 + k * iqr_val
    mask = np.zeros(arr.shape, dtype=bool)
    mask[~nan_mask] = (clean < lower) | (clean > upper)
    return {
        "mask": mask,
        "lower": float(lower),
        "upper": float(upper),
        "Q1": float(q1),
        "Q3": float(q3),
        "IQR": float(iqr_val),
    }


def zscore(x: np.ndarray, threshold: float = 3.0) -> dict:
    """Z-score 法：z = (x - μ) / σ，异常 if |z| > threshold（默认 threshold=3.0，σ 用总体标准差）。

    返回 {'mask': bool数组, 'z_scores': z值数组, 'threshold': threshold, 'mean': μ, 'std': σ}
    mask 中 NaN 位置恒为 False；z_scores 中 NaN 位置为 NaN。
    """
    arr = np.asarray(x, dtype=float)
    nan_mask = np.isnan(arr)
    clean = arr[~nan_mask]
    if clean.size == 0:
        return {
            "mask": nan_mask.copy(),
            "z_scores": np.full(arr.shape, np.nan),
            "threshold": threshold,
            "mean": float("nan"),
            "std": float("nan"),
        }
    mean = float(clean.mean())
    std = float(clean.std(ddof=0))  # 总体标准差（与 scipy.stats.zscore 默认一致）
    z = np.full(arr.shape, np.nan)
    z[~nan_mask] = (clean - mean) / std if std > 0 else 0.0
    mask = np.zeros(arr.shape, dtype=bool)
    mask[~nan_mask] = np.abs(z[~nan_mask]) > threshold
    return {
        "mask": mask,
        "z_scores": z,
        "threshold": threshold,
        "mean": mean,
        "std": std,
    }


def isolation_forest(
    X: np.ndarray,
    contamination: float = 0.1,
    n_estimators: int = 100,
    random_state: int = 42,
) -> dict:
    """Isolation Forest（sklearn 封装，不自实现）。

    原理：随机划分构造孤立树，异常点路径更短。decision_function 越小越异常，
    这里取负得到 anomaly score（越大越异常），便于与 IQR/Z-score 的 score 语义对齐。

    参数 X：二维数组 (n_samples, n_features)，调用方需保证无 NaN。
    返回 {'mask': bool数组(长度=n_samples), 'scores': 异常分数数组, 'contamination': contamination}
    """
    from sklearn.ensemble import IsolationForest

    X_arr = np.asarray(X, dtype=float)
    # 单变量时自动 reshape 为 (n, 1)
    if X_arr.ndim == 1:
        X_arr = X_arr.reshape(-1, 1)

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(X_arr)
    pred = model.predict(X_arr)  # -1=异常，1=正常
    raw_scores = model.decision_function(X_arr)  # 越小越异常
    scores = -raw_scores  # 取负：越大越异常
    mask = pred == -1
    return {
        "mask": mask.astype(bool),
        "scores": scores.astype(float),
        "contamination": contamination,
    }
