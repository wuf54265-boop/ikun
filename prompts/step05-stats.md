# Step 5: 统计分析模块

实现**相关性分析 + 假设检验 + 分布检验**。这是体现统计学硕士专业能力的核心模块——Pearson 相关系数、Welch t 检验、卡方独立性检验、KS 正态性检验全部自实现。

## 已有基础设施

```
stats_lib 骨架（全部 NotImplementedError，本次实现）：
├── core/stats_lib/correlation.py    # pearson_with_p()
├── core/stats_lib/hypothesis.py     # welch_t() / chi2_independence()
├── core/stats_lib/distribution.py   # ks_normality()

Schemas（Pydantic 已完整，无需改动）：
├── schemas/stats.py    # CorrelationRequest/Data, HypothesisRequest/Data, DistributionRequest/Data

Services / Routers（骨架已有，本次重写）：
├── services/stats.py     # correlation() / hypothesis() / distribution()
├── routers/stats.py      # 3 个 POST 端点（prefix="/analysis"）

前端：
├── app/dataset/[id]/stats/page.tsx  # 统计分析页（本次重写）
├── components/charts/ChartRenderer.tsx  # 已有图表渲染组件
```

---

## 第一部分：自实现统计算法（core/stats_lib/）

### 设计约束
- 核心计算用 **NumPy 手写**；CDF/p 值等底层数学函数可用 **SciPy**（`scipy.stats.t`, `scipy.stats.chi2`, `scipy.stats.norm`），此为合理边界
- 每个函数必须写**一行数学公式注释**
- 所有函数返回 dict，键名见下方定义
- NaN 安全：计算前剔除 NaN

---

### 1.1 Pearson 相关系数 + 显著性（correlation.py）

```
r = Σ(xi-x̄)(yi-ȳ) / √(Σ(xi-x̄)²·Σ(yi-ȳ)²)
显著性检验: t = r·√((n-2)/(1-r²)), df = n-2, 双尾 p 值由 t 分布得
```

函数签名：
```python
def pearson_with_p(X: np.ndarray) -> dict:
    """输入 X: (n_samples, n_features)，返回:
    {'r': 相关系数矩阵(n×n), 'p_values': p值矩阵(n×n)}"""
```

要求：
- 用 `np.cov` 或手写协方差均可，但不能调 `scipy.stats.pearsonr`
- 对每对变量计算 r → t → p（双尾）
- 对角线上 r=1.0, p=0.0
- 处理常数列（std=0）：r 返回 0 或 NaN，p 返回 NaN，不崩溃

---

### 1.2 Welch t 检验（hypothesis.py）

```
t = (x̄₁-x̄₂) / √(s₁²/n₁ + s₂²/n₂)
df = (s₁²/n₁ + s₂²/n₂)² / [ (s₁²/n₁)²/(n₁-1) + (s₂²/n₂)²/(n₂-1) ]    (Welch–Satterthwaite)
效应量: Cohen's d = |x̄₁-x̄₂| / √((s₁²+s₂²)/2)
```

函数签名：
```python
def welch_t(x: np.ndarray, y: np.ndarray) -> dict:
    """返回 {'statistic': t值, 'df': Welch自由度, 'p_value': 双尾p值, 'cohens_d': Cohen's d}"""
```

要求：
- 处理两组中任一组为空的边界情况（抛 ValueError 并说明原因）
- 处理两组方差均为 0 的退化情况（t=0 或 NaN，给出合理提示）

---

### 1.3 卡方独立性检验（hypothesis.py）

```
列联表 O(r×c), Eᵢⱼ = (行和ᵢ × 列和ⱼ) / N
χ² = Σ (O-E)²/E
df = (r-1)(c-1)
效应量: Cramér's V = √(χ² / (N · min(r-1, c-1)))
```

函数签名：
```python
def chi2_independence(cont_table: np.ndarray) -> dict:
    """输入 cont_table: 列联表 (r×c)，返回 {'statistic': χ², 'df': 自由度, 'p_value': p值, 'cramers_v': Cramér's V}"""
```

要求：
- 检查期望频数 E（任一格 < 1 或 >20% 格子 < 5 则在返回中加 `warning` 字段提示"期望频数过低，建议用 Fisher 精确检验"）
- 处理全零行/列（去掉再算，在返回中标记）

---

### 1.4 KS 正态性检验（distribution.py）

```
D = max |F_n(x) - Φ((x-x̄)/s)|
其中 F_n 为经验 CDF，Φ 为标准正态 CDF
显著性用 Lilliefors 修正临界值（n>50 时近似公式 D_crit ≈ 0.886/√n for α=0.05）
```

函数签名：
```python
def ks_normality(x: np.ndarray) -> dict:
    """返回 {'statistic': D, 'p_value': 近似p值, 'is_normal': D < D_crit(α=0.05)}"""
```

要求：
- 自实现经验 CDF 和正态参考 CDF 的比较逻辑
- 不直接调 `scipy.stats.kstest`（但可用 `scipy.stats.norm.cdf` 算正态 CDF）
- Lilliefors 临界值近似：n≤50 查表（硬编码），n>50 用 `0.886/√n`（α=0.05）
- n<5 时返回并注明"样本量过小，检验结果不可靠"

---

## 第二部分：统计分析服务（services/stats.py）

### 2.1 correlation(df, body)
- 若 body.columns 非空且 ≥2 列，只对指定列计算；否则对所有数值列计算
- 调用 `stats_lib.correlation.pearson_with_p()`
- 组装 CorrelationData（columns 列表 + matrix 二维列表 + p_values 二维列表）
- 所有值四舍五入到 4 位小数

### 2.2 hypothesis(df, body)
- test="welch_t"：取 body.group_column 分两组（二分类别列），body.value_column 为数值列，分别传入 `welch_t()`
- test="chi2"：若 body.cont_table 已给直接用；否则从 body.group_column + body.value_column 生成列联表
- 组装 HypothesisData（含 conclusion 字段：p<0.05→"拒绝原假设，存在显著差异/关联"，否则"无法拒绝原假设"）

### 2.3 distribution(df, body)
- 取 body.column 的数值列，调用 `ks_normality()`
- 组装 DistributionData（is_normal 根据临界值判定）

---

## 第三部分：连接路由（routers/stats.py）

修改现有骨架，三个端点分别调用 service 层：

- `POST /analysis/correlation` → `AnalysisResponse[CorrelationData]`
  - explanation 写明用的是 Pearson 积差相关，双尾检验
  
- `POST /analysis/hypothesis` → `AnalysisResponse[HypothesisData]`
  - explanation 中写明检验方法、原假设、自由度公式
  
- `POST /analysis/distribution` → `AnalysisResponse[DistributionData]`
  - explanation 中写明假设：H₀=数据服从正态分布，Lilliefors 修正

---

## 第四部分：前端统计分析页

重写 `frontend/app/dataset/[id]/stats/page.tsx`：

### 相关性分析区
- 数值列多选（至少选 2 列）
- "计算相关性"按钮 → POST /analysis/correlation
- **相关性热力图**：用 Recharts 或纯 CSS grid 渲染矩阵，单元格颜色深度代表 |r|，红=正相关、蓝=负相关，标注显著性星号（* p<.05, ** p<.01）
- 悬停显示：变量对、r 值、p 值

### 假设检验区
- 检验类型下拉（Welch t / 卡方）
- Welch t 模式：选择分组列（二分类别列）+ 数值列 + 运行按钮
- 卡方模式：选择行变量列 + 列变量列（均需类别列）+ 运行按钮
- 结果卡片：统计量、自由度、p 值、结论、效应量

### 分布检验区
- 选择数值列 + "检验正态性"按钮
- 结果卡片：KS 统计量 D、p 值、是否正态、分布直方图 + 正态拟合曲线

### 前端新增组件

`frontend/components/CorrelationHeatmap.tsx`:
- 基于相关性矩阵数据渲染热力图（CSS grid 实现，不额外依赖图表库）
- 每格背景色按 r 值映射颜色，标注显著性

---

## 第五部分：测试

新建 `backend/tests/step05_validate.py`：

- **test_pearson**：用已知数据验证 r 和 p 值。例如两组完全正相关 `x=[1,2,3], y=[2,4,6]` → r≈1.0；两组完全独立随机数据 r 应接近 0
- **test_welch_t**：两组有明显差异的数据（如 x=[10,11,12,13,14], y=[20,21,22,23,24]）→ p<0.05
- **test_chi2**：用经典列联表（如性别×偏好）验证 χ² 值与预期一致
- **test_ks_normality**：正态分布样本 (np.random.normal) → is_normal=True；均匀分布样本 → is_normal=False
- 所有测试与 `scipy.stats` 对照，容许浮点误差 ≤ 1e-6（p 值 ≤ 0.01）

---

## 需要输出的文件清单

### 后端
1. `backend/app/core/stats_lib/correlation.py` — 完整实现 pearson_with_p()
2. `backend/app/core/stats_lib/hypothesis.py` — 完整实现 welch_t() / chi2_independence()
3. `backend/app/core/stats_lib/distribution.py` — 完整实现 ks_normality()
4. `backend/app/services/stats.py` — 完整实现 correlation() / hypothesis() / distribution()
5. `backend/app/routers/stats.py` — 重写，连接 service 层

### 前端
6. `frontend/app/dataset/[id]/stats/page.tsx` — 重写完整统计分析页
7. `frontend/components/CorrelationHeatmap.tsx` — 新建

### 测试
8. `backend/tests/step05_validate.py` — 与 scipy 对照验证

---

## 验证清单

- [ ] Pearson: `[1,2,3]` vs `[2,4,6]` → r≈1.0, p≈0
- [ ] Welch t: 两组均值差异 10 → p<0.05
- [ ] 卡方: 独立性列联表 → χ² 与 scipy 误差 < 1e-6
- [ ] KS: 正态分布 → is_normal=True; 均匀分布 → is_normal=False
- [ ] curl POST /api/v1/analysis/correlation 返回 200
- [ ] curl POST /api/v1/analysis/hypothesis 返回 200
- [ ] curl POST /api/v1/analysis/distribution 返回 200

---

**每个算法函数必须包含一行数学公式注释。所有自实现函数核心计算用 NumPy，仅 CDF/p 值可用 SciPy。不可用 NotImplementedError 或 TODO 占位。**
