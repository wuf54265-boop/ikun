# Step 4: 数据清洗 + 异常检测

现在实现数据清洗和异常检测模块。**这是体现统计学专业能力的核心模块**——IQR 和 Z-score 必须用 NumPy 手写，不调 sklearn。

## 已有基础设施

```
已有（可直接 import 使用）：
├── backend/app/store/dataset_repo.py   # DatasetRepository: load_raw / save_clean / load_clean
├── backend/app/schemas/cleaning.py     # CleanRequest, CleanData, AnomalyRequest, AnomalyData, AnomalyPoint（Pydantic 已完整）
├── backend/app/schemas/common.py       # AnalysisResponse, Explanation
├── backend/app/routers/cleaning.py     # 两个端点骨架（POST /datasets/{id}/clean, POST /datasets/{id}/anomalies）
├── backend/app/utils/column_types.py   # is_numeric_type()

需本次实现（当前全是 NotImplementedError）：
├── backend/app/core/stats_lib/anomaly.py   # iqr() / zscore() / isolation_forest()
├── backend/app/services/cleaning.py        # apply_missing_strategies() / detect_anomalies()

前端已有：
├── frontend/app/dataset/[id]/clean/page.tsx  # 占位页（本次要重写）
├── frontend/components/AnalysisWizard.tsx     # 左侧导航
├── frontend/store/useDatasetStore.ts          # datasetId
```

---

## 第一部分：自实现异常检测算法（stats_lib/anomaly.py）

**这是整个项目最关键的差异化代码之一。务必完整实现，算法注释写清楚统计公式。**

### 1.1 IQR 法（自实现，纯 NumPy）

```
异常判定条件：x < Q1 - k*IQR 或 x > Q3 + k*IQR
其中 IQR = Q3 - Q1，默认 k=1.5
```

函数签名：
```python
def iqr(x: np.ndarray, k: float = 1.5) -> dict:
    """返回 {'mask': bool数组, 'lower': 下界, 'upper': 上界, 'Q1': ..., 'Q3': ..., 'IQR': ...}"""
```

### 1.2 Z-score 法（自实现，纯 NumPy）

```
z = (x - μ) / σ
异常判定：|z| > threshold（默认 3.0）
```

函数签名：
```python
def zscore(x: np.ndarray, threshold: float = 3.0) -> dict:
    """返回 {'mask': bool数组, 'z_scores': z值数组, 'threshold': threshold, 'mean': μ, 'std': σ}"""
```

### 1.3 Isolation Forest（封装 sklearn）

直接调用 `sklearn.ensemble.IsolationForest`，封装为与 iqr/zscore 一致的接口。不需要自实现。

函数签名：
```python
def isolation_forest(X: np.ndarray, contamination: float = 0.1, n_estimators: int = 100, random_state: int = 42) -> dict:
    """返回 {'mask': bool数组, 'scores': 异常分数数组, 'contamination': contamination}"""
```

### 实现要求
- 每个函数前写一行注释，给出核心数学公式
- iqr 和 zscore 只准 import numpy，不准调 sklearn/scipy
- 处理 NaN：计算统计量时忽略 NaN，但返回的 mask 中 NaN 位置记为 False（不算异常）
- isolation_forest 中 X 不应含 NaN，调用方负责预处理

---

## 第二部分：清洗服务（services/cleaning.py）

### 2.1 缺失值分析 + 处理

函数 `analyze_missing(df) -> dict`:
- 统计每列缺失数量、缺失率、缺失模式（随机/完全随机无法区分，标注"基于 MAR 假设"）
- 对每列给出推荐策略：缺失率<5%→删除行，5-30%→中位数(数值)/众数(类别)，>30%→建议用户手动判断并标注"高缺失警告"

函数 `apply_missing_strategies(df, body: CleanRequest, repo: DatasetRepository, dataset_id: str) -> CleanData`:
- 按用户选择的策略逐列处理（drop/mean/median/mode/fill）
- 将清洗后的 DataFrame 通过 `repo.save_clean()` 落盘
- 返回清洗前后对比：changed_columns, before_rows, after_rows

### 2.2 异常检测

函数 `detect_anomalies(df, body: AnomalyRequest) -> AnomalyData`:
- 根据 body.method 调用 stats_lib 中的 iqr/zscore/isolation_forest
- 仅对 body.columns 中指定的数值列检测（未指定则对所有数值列检测）
- 汇总所有列的异常点，返回 AnomalyData（含 method, anomaly_count, anomalies 列表）
- 每个 AnomalyPoint 包含 column, index（行号）, value, score（z-score 或异常分数）

---

## 第三部分：连接路由（修改 routers/cleaning.py）

修改现有骨架，将端点连接到 service 层：

### POST /datasets/{dataset_id}/clean
- 先从 `repo.load_raw()` 加载数据
- 调用 `services.cleaning.apply_missing_strategies()`
- 返回 `AnalysisResponse[CleanData]`，explanation 中说明用了什么策略及假设

### POST /datasets/{dataset_id}/anomalies
- 先从 `repo.load_raw()` 加载数据（如有 _clean 则优先用清洗后版本）
- 调用 `services.cleaning.detect_anomalies()`
- 返回 `AnalysisResponse[AnomalyData]`，explanation 中写明检测方法、阈值、公式

注意：检测异常前应对数值列做标准化提示（非强制），缺失值先剔除再检测。

---

## 第四部分：前端清洗页面（重写 clean/page.tsx）

重写 `frontend/app/dataset/[id]/clean/page.tsx`，实现：

### 缺失值处理区
- 每列一行：列名、缺失数量、缺失率进度条、推荐策略下拉框（drop/mean/median/mode/fill）、自定义填充值输入框
- "一键应用推荐策略"按钮
- "执行清洗"按钮 → 调用 POST /datasets/{id}/clean → 展示前后对比

### 异常检测区
- 方法选择：三个 tab（IQR / Z-score / Isolation Forest）
- IQR tab：调整 k 参数滑块（默认 1.5, 范围 0.5~5.0）
- Z-score tab：调整 threshold 滑块（默认 3.0, 范围 1.0~5.0）
- Isolation Forest tab：调整 contamination 滑块（默认 0.1, 范围 0.01~0.5）
- 列选择：多选要检测的数值列
- "检测异常"按钮 → 调用 POST /datasets/{id}/anomalies → 展示结果

### 异常结果展示
- 异常总数 + 各列异常分布摘要
- 异常点表格（列名、行号、值、异常分数）
- 每列的箱线图数据（后端返回 min/Q1/median/Q3/max/outliers，前端用 Recharts 画）

---

## 第五部分：前端新增组件

### `frontend/components/MissingValuePanel.tsx`
- 缺失值矩阵总览（简单的色块图：绿色=完整，黄色=缺失，每列一行）
- 每列缺失率进度条

### `frontend/components/AnomalyPanel.tsx`
- Tab 切换三种检测方法
- 参数调节控件
- 结果表格（可勾选处理）

---

## 技术约束

1. **stats_lib 纯函数**：iqr/zscore 只依赖 NumPy，入参 np.ndarray，出参 dict。不碰 pandas、FastAPI、DatasetRepository
2. **Isolation Forest 用 sklearn**：唯一例外，已在规划文档中明确取舍
3. **NaN 安全**：所有数值计算处理 NaN（mask NaN 位为 False，统计量计算时忽略 NaN）
4. **数据溯源**：清洗后数据另存为 `_clean.parquet`，不覆盖原始数据
5. **算法注释**：每个自实现函数上方写一行公式注释

---

## 需要输出的文件清单

### 后端
1. `backend/app/core/stats_lib/anomaly.py` — 完整实现 iqr / zscore / isolation_forest
2. `backend/app/services/cleaning.py` — 完整实现 analyze_missing / apply_missing_strategies / detect_anomalies
3. `backend/app/routers/cleaning.py` — 重写，连接 service 层

### 前端
4. `frontend/app/dataset/[id]/clean/page.tsx` — 重写完整清洗页
5. `frontend/components/MissingValuePanel.tsx` — 新建
6. `frontend/components/AnomalyPanel.tsx` — 新建

### 测试
7. `backend/tests/step04_validate.py` — 验证 iqr/zscore/isolation_forest 在已知数据上的输出正确性

---

## 验证清单

完成后请确认：
- [ ] `python -c "from app.core.stats_lib.anomaly import iqr, zscore, isolation_forest"` 不报错
- [ ] IQR 能正确检测已知异常值（如 `[1,2,3,4,100]` 中 100 被判异常）
- [ ] Z-score 能正确检测已知异常值（如 `[1,2,3,4,100]` 中 100 被判异常）
- [ ] Isolation Forest 能返回与输入行数一致的 mask
- [ ] curl POST /api/v1/datasets/{id}/clean 返回 200 和 CleanData
- [ ] curl POST /api/v1/datasets/{id}/anomalies 返回 200 和 AnomalyData
- [ ] 前端清洗页能正常渲染三个区域

---

**每个文件标注完整路径，不可以用 NotImplementedError 或 TODO 占位。算法函数必须包含公式注释。**
