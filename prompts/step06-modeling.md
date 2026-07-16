# Step 6: 建模分析模块

实现 **OLS 线性回归 + K-Means 聚类**，全部自实现。这是整个项目技术含金量最高的模块——面试时展示的核心代码。

## 已有基础设施

```
stats_lib 骨架（本次完整实现）：
├── core/stats_lib/ols.py       # ols() 函数骨架
├── core/stats_lib/kmeans.py    # kmeans() 函数骨架

Schemas（本次需补 dataset_id）：
├── schemas/modeling.py  # RegressionRequest/Data, ClusteringRequest/Data — 基本完整

Services / Routers 骨架：
├── services/modeling.py  # regression() / clustering()
├── routers/modeling.py   # POST /modeling/regression, POST /modeling/clustering

前端：
├── app/dataset/[id]/model/page.tsx  # TODO 占位页（本次重写）
```

---

## 第一部分：OLS 线性回归（core/stats_lib/ols.py）

### 算法原理

```
系数: β = (XᵀX)⁻¹Xᵀy，用 np.linalg.solve 解正规方程（比显式求逆更稳定）
拟合: ŷ = Xβ，残差 e = y − ŷ
推断: σ² = RSS/(n−p)，se(βⱼ) = √(σ²·diag((XᵀX)⁻¹)ⱼ₊₁)，tⱼ = βⱼ/se(βⱼ)
p 值: 双尾 t 分布（scipy.stats.t 取 CDF，合理边界）
R² = 1 − RSS/TSS，调整 R² = 1 − (1−R²)(n−1)/(n−p−1)
```

### 函数签名

```python
def ols(X: np.ndarray, y: np.ndarray, standardize: bool = False) -> dict:
    """返回:
    {
      'coefficients': [{'name': 'const', 'coef':..., 'std_err':..., 't':..., 'p_value':...}, ...],
      'r_squared': float,
      'adj_r_squared': float,
      'residuals': ndarray,       # e = y − ŷ
      'fitted': ndarray,          # ŷ
      'residual_std': float,       # √σ²
    }
    """
```

### 实现要求

1. **自动添加截距项**：X 第一列自动插入全 1 列（除非用户明确不需要，可用 add_intercept=True 控制）
2. **标准误/推断必须自实现**：从 (XᵀX)⁻¹ 和 σ² 手工推导，不能调 statsmodels
3. **标准化系数**：standardize=True 时对 X（不含截距列）和 y 做 z-score 标准化后回归，方便比较特征重要性
4. **数值稳定性**：
   - 用 `np.linalg.solve(XᵀX, Xᵀy)` 而非 `np.linalg.inv(XᵀX) @ Xᵀy`
   - XᵀX 接近奇异时（条件数 > 1e10），在结果中附加 warning："特征矩阵接近奇异，可能存在多重共线性"
5. **残差诊断**：返回残差数组供前端画残差图（residuals vs fitted, Q-Q plot data）

---

## 第二部分：K-Means 聚类（core/stats_lib/kmeans.py）

### 算法原理

```
初始化: k-means++（按与已选质心距离平方比例选下一个质心）
迭代:
  ① 每个样本分配到最近质心（欧氏距离）
  ② 质心更新为簇内均值
  ③ 重复至 max_iter 或质心位移 < tol

选 K:
  肘部法则: 画不同 K 的 inertia = Σ‖x−μ‖²
  轮廓系数: s(i) = (b(i)−a(i)) / max(a(i), b(i))
    其中 a(i)=样本i到同簇其他点平均距离，b(i)=到最近其他簇平均距离
```

### 函数签名

```python
def kmeans(X: np.ndarray, k: int, max_iter: int = 300, tol: float = 1e-4, seed: int = 42) -> dict:
    """返回:
    {
      'labels': ndarray (n,),       # 簇标签 0..k-1
      'centroids': ndarray (k, d),   # 质心坐标
      'inertia': float,              # Σ‖x−μ‖²
      'iterations': int,             # 实际迭代次数
    }
    """

def silhouette_score(X: np.ndarray, labels: np.ndarray) -> float:
    """计算轮廓系数。自实现，不调 sklearn.metrics.silhouette_score。"""

def select_k(X: np.ndarray, k_range: range = range(2, 11), seed: int = 42) -> dict:
    """返回:
    {
      'best_k': int,
      'inertias': [float, ...],        # 每个 k 的 inertia（用于肘部图）
      'silhouettes': [float, ...],      # 每个 k 的 silhouette（用于选择）
    }
    """
```

### 实现要求

1. **k-means++ 初始化**：首点随机选，后续点按距离平方概率选（必须自实现，不能调 sklearn）
2. **空簇处理**：迭代中出现空簇时重新随机初始化该质心，记录 warning
3. **轮廓系数自实现**：两两距离矩阵用 `np.linalg.norm` 或向量化计算，避免 Python 循环
4. **收敛判定**：质心位移 max(|μ_new − μ_old|) < tol 或达 max_iter
5. **auto_k 模式**：k_range 默认 2~10，选择最高平均轮廓系数对应的 k（若轮廓系数均 < 0.3 则警告"聚类结构弱"）

---

## 第三部分：建模服务（services/modeling.py）

### regression(df, body)
- 取 body.features 作为自变量，body.target 作为因变量
- 所有变量必须是数值列
- 剔除 NaN 行（完整观测）
- 调用 `ols()` 并组装 RegressionData
- residual_plot 字典包含 `{'residuals': [...], 'fitted': [...], 'qq_data': [...]}`
  - qq_data 计算：对残差排序后与理论正态分位数比较（用 scipy.stats.norm.ppf）

### clustering(df, body)
- 取 body.features 作为聚类特征
- 标准化特征（z-score）后聚类
- body.auto_k=True 时调用 select_k 自动选 K
- 返回 ClusteringData（含 labels, centroids, inertia, silhouette, cluster_sizes）

---

## 第四部分：连接路由（routers/modeling.py）

- POST /modeling/regression → AnalysisResponse[RegressionData]
- POST /modeling/clustering → AnalysisResponse[ClusteringData]
- 数据集加载用 `_load_analysis_df`（优先 _clean 版本）
- 补 `dataset_id` 到 Request schema（参考 Step 5 的做法）
- explanation 中写明：OLS 正规方程自实现 vs 调用 statsmodels/sklearn 的区别；K-Means k-means++ 初始化自实现

---

## 第五部分：Schema 补全（schemas/modeling.py）

在 Request 中加 `dataset_id: str`：
- RegressionRequest 补 `dataset_id`
- ClusteringRequest 补 `dataset_id`
- RegressionData 中 `residual_plot` 改为更具体的 dict 结构或保持 dict

---

## 第六部分：前端建模页

重写 `frontend/app/dataset/[id]/model/page.tsx`：

### OLS 回归区
- 目标变量下拉（数值列）
- 特征变量多选（数值列，排除已选目标）
- "标准化系数"复选框
- "运行回归"按钮
- 结果：
  - **系数表**：variable / coef / std_err / t / p_value，p<0.05 行高亮绿色
  - **模型摘要**：R²、调整 R²
  - **残差诊断图**：Recharts ScatterChart（残差 vs 拟合值）+ Q-Q plot（理论分位 vs 实际分位）

### K-Means 聚类区
- 特征列多选
- K 值选择：手动输入 / 自动（肘部+轮廓系数）
- "运行聚类"按钮
- 结果：
  - **肘部图 + 轮廓系数图**：K vs inertia / K vs silhouette
  - **聚类散点图**：Recharts ScatterChart（前两个特征为 x/y，簇颜色区分，质心标星号）
  - **各簇规模**：柱状图

### 前端新增组件
- `frontend/components/CoefficientTable.tsx` — 回归系数表
- `frontend/components/ClusterChart.tsx` — 聚类散点图 + 肘部轮廓图

---

## 第七部分：测试

新建 `backend/tests/step06_validate.py`：

- **test_ols**：用已知数据验证 β。如 y=2x₁+3x₂+1，OLS 应恢复出近似系数。与 `statsmodels.OLS` 对照（β 误差 < 1e-6, R² 误差 < 1e-6）
- **test_ols_multicollinearity**：构造接近共线性的数据（x₂≈2x₁），验证 warning 字段
- **test_kmeans**：Iris 前两维特征上聚类（k=3），验证标签无空簇，且与 `sklearn.cluster.KMeans` 的调整兰德指数(ARI) ≥ 0.7
- **test_silhouette**：单簇数据 silhouette≈0，明显分离数据 silhouette>0.5
- **test_empty_cluster**：构造极端数据使某次迭代出现空簇，验证 reinit 逻辑

---

## 需要输出的文件清单

### 后端
1. `backend/app/core/stats_lib/ols.py` — 完整实现 ols()
2. `backend/app/core/stats_lib/kmeans.py` — 完整实现 kmeans() / silhouette_score() / select_k()
3. `backend/app/services/modeling.py` — 完整实现 regression() / clustering()
4. `backend/app/routers/modeling.py` — 重写，连接 service
5. `backend/app/schemas/modeling.py` — 补 dataset_id，优化 residual_plot

### 前端
6. `frontend/app/dataset/[id]/model/page.tsx` — 重写完整建模页
7. `frontend/components/CoefficientTable.tsx` — 新建
8. `frontend/components/ClusterChart.tsx` — 新建

### 测试
9. `backend/tests/step06_validate.py` — 与 statsmodels/sklearn 对照

---

## 验证清单

- [ ] OLS: y=2x₁+3x₂+1 → β 恢复误差 < 1e-6
- [ ] OLS: 系数表包含标准误 / t / p / R² / 调整 R²
- [ ] OLS: 共线性数据产生 warning
- [ ] K-Means: Iris 上与 sklearn KMeans ARI ≥ 0.7
- [ ] K-Means: k-means++ 初始化自实现（不调 sklearn）
- [ ] K-Means: 轮廓系数自实现（不调 sklearn）
- [ ] K-Means: auto_k 模式能找到合理 K
- [ ] curl POST /api/v1/modeling/regression 返回 200
- [ ] curl POST /api/v1/modeling/clustering 返回 200

---

**每个算法函数必须包含数学公式注释。OLS 必须自实现推断（se/t/p）。K-Means 必须自实现 k-means++ 和轮廓系数。不可用 sklearn 替代核心算法（仅对照测试可用）。**
