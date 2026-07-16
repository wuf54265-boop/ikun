# Step 8: 行业模板 + 方法展示页

实现 **RFM 用户分层 + 漏斗转化分析** 两个电商行业模板，以及完善 `/methods` 算法展示页。这是 P1 阶段的收尾——完成后项目核心功能完整。

## 已有基础设施

```
stats_lib 骨架（本次实现）：
├── core/stats_lib/rfm.py      # rfm_analysis() 骨架 — NotImplementedError
├── core/stats_lib/funnel.py   # funnel_analysis() 骨架 — NotImplementedError

Schemas（已完整，无需改动）：
├── schemas/templates.py   # RFMRequest/Data, FunnelRequest/Data — Pydantic 模型完整

Services / Routers：
├── services/templates.py  # rfm() / funnel() 骨架
├── routers/templates.py   # POST /templates/rfm, POST /templates/funnel

前端：
├── app/dataset/[id]/templates/page.tsx  # TODO 占位页（本次重写）
├── app/methods/page.tsx                 # 已有基础表格（本次增强）
```

---

## 第一部分：RFM 引擎（core/stats_lib/rfm.py）

### 算法描述

```
输入：交易表 + customer_id 列 + date 列 + amount 列
步骤：
1. 聚合：按 customer_id 分组，计算
   R = (snapshot_date - 最近购买日期).days  （天数，越小越好）
   F = 购买次数                         （次数，越大越好）
   M = 总金额                           （金额，越大越好）
2. 打分（五分位）：对 R、F、M 分别按五分位（20%/40%/60%/80%分位点）打分 1-5
   - R：值越小分越高（最近购买的得高分），打分为 5-分值+1
   - F：值越大分越高（频繁购买的得高分），直接用分位序号+1
   - M：同 F
3. 组合分群：根据 RFM 分数组合分配标签
   - R≥4,F≥4,M≥4 → "冠军客户"（重要价值）
   - R≥4,F<3,M≥3 → "潜力客户"（最近活跃但购买少）
   - R<3,F≥4,M≥4 → "忠诚客户"（需唤醒）
   - R<3,F<3,M≥3 → "流失风险"
   - R<3,F<3,M<3 → "已流失"
   - 其余 → "一般客户"
4. 输出：各分群的人数、占比、运营建议文本
```

### 函数签名

```python
def rfm_analysis(df: pd.DataFrame, customer_id: str, date: str, amount: str, snapshot_date=None) -> dict:
    """返回:
    {
      'segments': [{'segment': str, 'count': int, 'share': float}, ...],
      'matrix': [{'customer_id': str, 'R': int, 'F': int, 'M': int, 'score_r': int, 'score_f': int, 'score_m': int, 'segment': str}, ...],
      'suggestions': [str, ...],   # 运营建议
    }
    """
```

### 要求
- date 列自动 `pd.to_datetime()` 解析
- snapshot_date 默认为 date 列最大值
- 处理后返回 top 500 客户的 matrix（防数据过大）
- 纯 pandas + numpy 实现，不调 sklearn

---

## 第二部分：漏斗分析引擎（core/stats_lib/funnel.py）

### 算法描述

```
输入：DataFrame + 步骤列名列表（按漏斗顺序）
计算每步：
  - users: 该步骤列非空/非0 的行数
  - conversion: 当前步人数 / 第一步人数 × 100%（总体转化率）
流失点 = conversion 降幅最大的相邻两步
```

### 函数签名

```python
def funnel_analysis(df: pd.DataFrame, steps: list[str]) -> dict:
    """返回:
    {
      'steps': [{'step': str, 'users': int, 'conversion': float}, ...],
      'bottleneck': str | None,  # 流失最大的步骤（"步骤A→步骤B"）
    }
    """
```

### 要求
- 每步统计该列非空/非0的行数
- 若某列全部非空则 users = 总行数
- 纯 pandas + numpy

---

## 第三部分：服务层 + 路由（services/templates.py, routers/templates.py）

### services/templates.py
- `rfm(df, body)` → 调用 `stats_lib.rfm.rfm_analysis()`
- `funnel(df, body)` → 调用 `stats_lib.funnel.funnel_analysis()`

### routers/templates.py
- 补 `dataset_id` 到 Request（本次需要在 schema 中加）
- POST /templates/rfm → AnalysisResponse[RFMData]
- POST /templates/funnel → AnalysisResponse[FunnelData]
- explanation 中写明方法原理和假设

### schemas/templates.py
- RFMRequest 补 `dataset_id: str`
- FunnelRequest 补 `dataset_id: str`

---

## 第四部分：前端行业模板页

重写 `frontend/app/dataset/[id]/templates/page.tsx`：

### RFM 分析区
- 三列映射选择器：客户 ID 列、日期列、金额列
- 快照日期输入（日期选择器，默认今天）
- "运行 RFM 分析"按钮
- 结果：
  - **分群占比饼图/柱状图**（Recharts PieChart）
  - **分群表**：segment / count / share
  - **运营建议**列表

### 漏斗分析区
- 步骤列多选（按顺序选，可拖拽排序或上下移动）
- "运行漏斗分析"按钮
- 结果：
  - **漏斗图**（用 Recharts 的 BarChart 或自定义漏斗组件）
  - 每步：step name / users / 转化率%
  - **瓶颈标注**：流失最大的步骤高亮红色

---

## 第五部分：方法展示页增强

增强 `frontend/app/methods/page.tsx`：

当前页面只有一个简单表格。需要增强为：

1. **算法卡片网格**：每个方法一张卡片，包含：
   - 方法名 + 实现方式标签（自实现/sklearn）
   - **数学公式**（如 β = (XᵀX)⁻¹Xᵀy）
   - 用途说明一句话
   - 如果是自实现：标注"已验证与 scipy/sklearn 对照通过"
   - 如果是 sklearn：标注取舍理由

2. **对照结果展示**（可选）：在卡片底部用一行小字展示验证结果，例如：
   - OLS："与 statsmodels 对照，β 误差 < 1e-6，R² 误差 < 1e-6"
   - K-Means："Iris 4 维全特征，与 sklearn KMeans 对照 ARI ≥ 0.7"

3. **技术栈总结**区域（页面底部）：
   - 前端：Next.js + TailwindCSS + Recharts + Zustand
   - 后端：FastAPI + Pandas + NumPy + SciPy
   - AI：OpenAI API（仅翻译结构化结果，不做计算）
   - 存储：Parquet + SQLite

### 需要的公式清单

| 方法 | 公式 |
|------|------|
| OLS | β = (XᵀX)⁻¹Xᵀy |
| K-Means | min Σ‖xᵢ − μ_cᵢ‖² |
| Welch t | t = (x̄₁−x̄₂)/√(s₁²/n₁+s₂²/n₂) |
| 卡方 | χ² = Σ(O−E)²/E, E = (行和×列和)/N |
| KS 正态性 | D = max｜F_n(x) − Φ((x−x̄)/s)｜ |
| Pearson | r = Σ(xᵢ−x̄)(yᵢ−ȳ)/√(Σ(xᵢ−x̄)²·Σ(yᵢ−ȳ)²) |
| IQR | 异常 if x < Q1−k·IQR or x > Q3+k·IQR |
| Z-score | z = (x−μ)/σ, ｜z｜> threshold 判异常 |
| RFM | R=最近天数, F=购买次数, M=总金额→五分位打分 |
| 漏斗 | conv_i = users_i / users_first × 100% |

---

## 第六部分：首页 Demo 数据集

修改 `frontend/app/page.tsx`：

在现有落地页基础上添加一个 **"体验 Demo"区域**：
- 一个卡片/按钮：使用内置示例数据快速体验
- 点击后调用后端一个新增接口 `POST /api/v1/datasets/demo`，返回一个预设的 demo dataset_id
- 然后跳转到 `/dataset/{demo_id}/overview`

新建后端接口：
- `POST /api/v1/datasets/demo` → 用 `DatasetRepository` 创建一个内置的电商示例数据集并返回 dataset_id
- Demo 数据：约 500 行交易数据，含 customer_id / order_date / amount / quantity / category / is_member / channel 列（用 NumPy 随机生成，但设定固定的 seed=42 保证可复现）

---

## 需要输出的文件清单

### 后端
1. `backend/app/core/stats_lib/rfm.py` — 完整实现 rfm_analysis()
2. `backend/app/core/stats_lib/funnel.py` — 完整实现 funnel_analysis()
3. `backend/app/services/templates.py` — 完整实现 rfm() / funnel()
4. `backend/app/routers/templates.py` — 重写，连接 service
5. `backend/app/schemas/templates.py` — 补 dataset_id
6. `backend/app/routers/datasets.py` — 新增 POST /datasets/demo 端点

### 前端
7. `frontend/app/dataset/[id]/templates/page.tsx` — 重写完整模板页
8. `frontend/app/methods/page.tsx` — 增强算法展示页
9. `frontend/app/page.tsx` — 添加 Demo 体验入口

---

## 验证清单

- [ ] RFM: curl POST /api/v1/templates/rfm 返回 200，segments 含冠军/忠诚/流失等分群
- [ ] 漏斗: curl POST /api/v1/templates/funnel 返回 200，各步转化率正确
- [ ] Demo: curl POST /api/v1/datasets/demo 返回 200 和有效 dataset_id
- [ ] /methods 页展示了所有 11 项算法及公式
- [ ] 模板页 RFM 和漏斗两个 Tab 正常切换和渲染
- [ ] 首页 Demo 按钮可一键体验

---

**RFM 分群逻辑按指定规则实现（R≥4,F≥4,M≥4→冠军…）。每个算法函数包含一行公式注释。**
