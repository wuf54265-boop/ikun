"""K-Means 聚类（自实现）。

算法流程
--------
初始化（k-means++）：首心随机；第 c 个质心按 D(x)² 概率选，D(x)=min_k ‖x−μ_k‖²
迭代（Lloyd）：
  ① 分配：每个样本归入最近质心（欧氏距离）  label_i = argmin_k ‖x_i − μ_k‖²
  ② 更新：μ_k = 簇内样本均值
  ③ 收敛：max_k ‖μ_k^new − μ_k^old‖ < tol 或达 max_iter
空簇处理：某次迭代某簇无样本 → 该质心随机重置（从数据点中采样），并记 warning

选 K
----
肘部法则：inertia(k) = Σ_i ‖x_i − μ_{label_i}‖²，随 k 增大下降趋缓处为「肘」
轮廓系数（自实现）：
  a(i) = 样本 i 到同簇其他点平均距离
  b(i) = 样本 i 到最近其他簇平均距离
  s(i) = (b(i) − a(i)) / max(a(i), b(i))，全局 silhouette = mean_i s(i)
  auto_k 取使平均轮廓系数最大的 k；若最高 s < 0.3 提示「聚类结构弱」

核心算法（k-means++ / 轮廓系数）均自实现，不调用 sklearn；sklearn 仅用于测试对照。
"""
import numpy as np


def _pairwise_sq_dists(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """(n,d) 与 (m,d) 的逐对欧氏距离平方：‖a−b‖² = ‖a‖² − 2a·b + ‖b‖²（向量化）。"""
    na = np.sum(A * A, axis=1)[:, None]          # (n,1)
    nb = np.sum(B * B, axis=1)[None, :]          # (1,m)
    cross = A @ B.T                              # (n,m)
    return np.clip(na - 2.0 * cross + nb, 0.0, None)


def _kmeanspp_init(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """k-means++ 初始化：首心随机，其余按到已选质心最近距离平方的比例概率选取。"""
    n, d = X.shape
    centroids = np.empty((k, d), dtype=float)
    # 首心随机
    first = int(rng.integers(n))
    centroids[0] = X[first]
    # 各点到「已选质心」的最近距离平方
    closest_sq = _pairwise_sq_dists(X, centroids[0:1]).ravel()
    for c in range(1, k):
        total = float(closest_sq.sum())
        if total <= 0.0:
            # 所有点重合，随便选一个
            idx = int(rng.integers(n))
        else:
            probs = closest_sq / total
            idx = int(rng.choice(n, p=probs))
        centroids[c] = X[idx]
        dist_new = _pairwise_sq_dists(X, centroids[c : c + 1]).ravel()
        closest_sq = np.minimum(closest_sq, dist_new)
    return centroids


def kmeans(
    X: np.ndarray,
    k: int,
    max_iter: int = 300,
    tol: float = 1e-4,
    seed: int = 42,
):
    """K-Means（k-means++ 初始化 + Lloyd 迭代，自实现）。

    返回 {'labels', 'centroids', 'inertia', 'iterations', 'warnings'}。
    """
    X = np.asarray(X, dtype=float)
    n, d = X.shape
    if k <= 0:
        raise ValueError("k 必须为正整数")
    if k > n:
        raise ValueError(f"k({k}) 不能大于样本数({n})")
    rng = np.random.default_rng(seed)

    centroids = _kmeanspp_init(X, k, rng)
    warnings: list[str] = []

    labels = np.zeros(n, dtype=int)
    iterations = 0
    for it in range(max_iter):
        # ① 分配：每个样本归入最近质心
        sq = _pairwise_sq_dists(X, centroids)          # (n, k)
        new_labels = np.argmin(sq, axis=1)

        # ② 更新质心 = 簇内均值
        new_centroids = np.empty_like(centroids)
        for j in range(k):
            pts = X[new_labels == j]
            if pts.shape[0] > 0:
                new_centroids[j] = pts.mean(axis=0)
            else:
                # 空簇：随机重置并记 warning
                warnings.append(f"迭代 {it}: 簇 {j} 为空，已随机重置质心")
                new_centroids[j] = X[int(rng.integers(n))]

        # ③ 收敛判定：最大质心位移 < tol
        shift = float(np.max(np.abs(new_centroids - centroids)))
        centroids = new_centroids
        labels = new_labels
        iterations = it + 1
        if shift < tol:
            break

    # 用最终质心重新分配，保证 labels 与 centroids 一致
    sq = _pairwise_sq_dists(X, centroids)
    labels = np.argmin(sq, axis=1)
    inertia = float(np.sum(np.min(sq, axis=1)))  # Σ ‖x − μ_label‖²

    return {
        "labels": labels,
        "centroids": centroids,
        "inertia": inertia,
        "iterations": iterations,
        "warnings": warnings,
    }


def silhouette_score(X: np.ndarray, labels: np.ndarray) -> float:
    """轮廓系数（自实现，向量化距离矩阵）。

    s(i) = (b(i) − a(i)) / max(a(i), b(i))，全局取均值。
    簇数 <2 或每个点自成一簇时定义为 0（无结构可评）。
    """
    X = np.asarray(X, dtype=float)
    labels = np.asarray(labels)
    n = X.shape[0]
    uniq = np.unique(labels)
    k = len(uniq)
    if k < 2 or k >= n:
        return 0.0

    # 全点对距离（sqrt 后）
    D = np.sqrt(_pairwise_sq_dists(X, X))
    np.fill_diagonal(D, 0.0)

    sil = np.zeros(n, dtype=float)
    for ci in uniq:
        idx = np.where(labels == ci)[0]
        size_c = idx.size
        if size_c <= 1:
            sil[idx] = 0.0
            continue
        # a(i)：到同簇其他点平均距离（对角线为 0，除以 size_c−1）
        within = D[np.ix_(idx, idx)]
        a = within.sum(axis=1) / (size_c - 1)
        # b(i)：到各其他簇平均距离的最小值
        b_list = []
        for cj in uniq:
            if cj == ci:
                continue
            jdx = np.where(labels == cj)[0]
            b_list.append(D[np.ix_(idx, jdx)].mean(axis=1))
        b = np.min(np.stack(b_list, axis=1), axis=1)
        # s(i) = (b−a) / max(a, b)；max 同时保证分母非负、避免除零
        s = (b - a) / np.maximum(a, b)
        # a==b==0 时定义为 0
        s = np.where((a == 0) & (b == 0), 0.0, s)
        sil[idx] = s
    return float(np.mean(sil))


def select_k(X: np.ndarray, k_range: range = range(2, 11), seed: int = 42) -> dict:
    """肘部 + 轮廓系数自动选 K。

    返回 {'best_k', 'inertias', 'silhouettes', 'warning'}。
    best_k = 使平均轮廓系数最大的 k；若最高 s < 0.3 记 warning「聚类结构弱」。
    """
    X = np.asarray(X, dtype=float)
    inertias: list[float] = []
    silhouettes: list[float] = []
    best_k = None
    best_sil = -np.inf
    for k in k_range:
        res = kmeans(X, k, seed=seed)
        inertias.append(float(res["inertia"]))
        sil = silhouette_score(X, res["labels"])
        silhouettes.append(sil)
        if sil > best_sil:
            best_sil = sil
            best_k = k
    warning = None
    if best_sil < 0.3:
        warning = f"聚类结构弱（最高平均轮廓系数={best_sil:.3f}<0.3），建议人工复核或尝试降维"
    return {
        "best_k": best_k,
        "inertias": inertias,
        "silhouettes": silhouettes,
        "warning": warning,
    }
