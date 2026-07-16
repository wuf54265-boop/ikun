# Step 3: 数据上传 + 自动数据理解

现在实现 P0 功能：**数据上传和自动数据理解模块**。

## 已存在的基础设施（请先读取，不要重写）

本次开发基于 Step 2 已完成的项目骨架。以下文件已存在且可直接调用：

### 后端已有文件
```
backend/app/
├── config.py              # Settings: max_upload_mb, sample_rows, data_dir, db_path
├── main.py                # FastAPI app, 已装配 routers
├── dependencies.py        # get_dataset_repo 依赖注入
├── store/
│   ├── db.py              # init_db() — SQLite 建表
│   └── dataset_repo.py    # DatasetRepository: save_raw/load_raw/save_clean/load_clean/get_metadata/delete
├── utils/
│   └── io.py              # read_table_file(raw, filename) — CSV/Excel 解析，UTF-8/GBK 回退
├── schemas/
│   ├── common.py          # AnalysisResponse[T], Explanation, Meta
│   └── dataset.py         # ColumnInfo, UploadResponse
├── routers/
│   └── datasets.py        # POST /datasets/upload, GET /datasets, GET /datasets/{id} — 骨架已有
└── services/
    └── ingestion.py       # ingest(raw, filename) — 骨架已有但未实现
```

### 前端已有文件
```
frontend/
├── lib/
│   ├── api.ts             # apiGet, apiPost, uploadFile (BASE 已配置)
│   └── types.ts           # AnalysisResponse, UploadResponse, ColumnInfo
├── store/
│   ├── useDatasetStore.ts # datasetId, filename, setDataset(), clear()
│   └── useAnalysisStore.ts
└── app/
    ├── layout.tsx         # RootLayout with Nav
    └── page.tsx           # 落地页（已有「上传数据」链接到 /upload）
```

---

## 本次需要实现的内容

### 后端 — 第一部分：完善数据接入（ingestion）

修改 `backend/app/services/ingestion.py`：
1. 调用 `read_table_file(raw, filename)` 解析为 DataFrame
2. 检测大文件（行数 > settings.sample_rows），自动随机采样并附注
3. 调用 `DatasetRepository.save_raw(df, filename)` 落盘 Parquet 并写 SQLite 元数据
4. 实现列类型推断逻辑：对每列判断为 numeric / categorical / datetime / text / boolean，给出置信度
5. 对数值列计算基础统计（均值/中位数/标准差/最小值/最大值/分位数），对分类列计算唯一值数和 Top5 值
6. 组装并返回 `UploadResponse`（含 dataset_id, filename, rows, cols, columns 列表, 前20行预览）

### 后端 — 第二部分：数据理解（profiling）

创建/修改以下文件：

`backend/app/services/profiling.py`:
1. `profile_dataset(df)` — 返回字段字典：每列的类型/置信度/描述统计/缺失率/唯一值数
2. `quality_report(df)` — 返回数据质量报告：缺失率、重复行数、常量列检测、高基数ID提示、综合质量评分(0-100)

`backend/app/routers/profiling.py` (修改现有骨架):
- `GET /datasets/{dataset_id}/profile` — 调用 `repo.load_raw()` 然后 `profile_dataset()`
- `GET /datasets/{dataset_id}/quality` — 调用 `repo.load_raw()` 然后 `quality_report()`
- 返回格式为 `AnalysisResponse[ProfileResponse]`

`backend/app/schemas/profiling.py` (修改现有骨架):
- 定义 `ProfileResponse`, `QualityResponse` 以及相关子模型

### 后端 — 第三部分：增强编码探测

修改 `backend/app/utils/io.py`：
- 在现有 UTF-8 → GBK 回退基础上，增加 gb2312、gb18030、latin-1 的回退链
- 增加空文件检测（抛出明确错误）

### 后端 — 第四部分：连接 routers

修改 `backend/app/routers/datasets.py`：
- 将 POST /datasets/upload 连接到 `services.ingestion.ingest()`
- 确保返回值为 `AnalysisResponse[UploadResponse]`

### 前端 — 上传页面

创建文件：
1. `frontend/app/upload/page.tsx` — 上传页面：
   - 拖拽上传区域（支持点击选择文件）
   - 文件类型校验（.csv, .xlsx, .xls）
   - 文件大小校验（50MB 上限）
   - 上传进度条
   - 上传成功后：
     - 调用 `useDatasetStore.setDataset(id, filename)` 存状态
     - 展示数据预览表格（前20行，分页）
     - 展示字段类型标签和统计摘要卡片
     - 「下一步：数据清洗」按钮导航到 `/dataset/[id]/clean`

### 前端 — 数据概览页面

创建文件：
1. `frontend/app/dataset/[id]/overview/page.tsx` — 数据概览页：
   - 调用 GET /datasets/{id}/profile 和 GET /datasets/{id}/quality
   - 字段信息卡片网格：每列一个卡片，含类型标签、分布迷你图、缺失率指示
   - 数据质量面板：综合评分（仪表盘样式）、问题清单、警告列表
   - 使用左侧分析向导导航条（概览→清洗→统计→建模→模板→报告）

---

## 技术约束

1. **存储**：所有 DataFrame 落盘通过 `DatasetRepository`，不在内存中长时间持有大 DataFrame
2. **响应格式**：所有 API 返回 `AnalysisResponse[T]`，explanation 字段必须填写 method/assumptions/interpretation
3. **类型推断逻辑**：优先基于 pandas dtype 判断，再用正则/采样辅助（如判断是否日期格式、布尔值）
4. **性能**：50MB / 10万行场景下，上传+解析+类型推断 < 10秒
5. **错误处理**：文件格式错误、编码失败、空文件、超大文件都要返回明确错误信息
6. **采样策略**：行数超 sample_rows 时，随机采样并标注"基于 N 行样本分析"

---

## 需要输出的文件清单

### 后端
1. `backend/app/services/ingestion.py` — 完整实现
2. `backend/app/services/profiling.py` — 完整实现
3. `backend/app/routers/datasets.py` — 重写（连接 ingestion）
4. `backend/app/routers/profiling.py` — 重写（连接 profiling）
5. `backend/app/schemas/profiling.py` — 完整 Pydantic 模型
6. `backend/app/utils/io.py` — 增强编码探测

### 前端
7. `frontend/app/upload/page.tsx` — 新建上传页
8. `frontend/app/dataset/[id]/overview/page.tsx` — 新建概览页
9. `frontend/components/FileDropzone.tsx` — 拖拽上传组件
10. `frontend/components/DataPreview.tsx` — 数据预览表格组件
11. `frontend/components/AnalysisWizard.tsx` — 分析向导导航组件（修改现有骨架）

---

## 验证清单

完成后请确认：
- [ ] `uvicorn app.main:app` 启动无报错
- [ ] `curl -X POST http://localhost:8000/api/v1/datasets/upload -F "file=@test.csv"` 返回 200 和正确的 UploadResponse
- [ ] `curl http://localhost:8000/api/v1/datasets/{id}/profile` 返回字段统计信息
- [ ] `curl http://localhost:8000/api/v1/datasets/{id}/quality` 返回质量报告
- [ ] 前端 `npm run dev` 后访问 /upload 能正常渲染拖拽区
- [ ] 上传文件后能跳转到概览页看到数据预览

---

**请严格按照上述要求完成代码，每个文件标注完整路径，不要省略任何实现细节。如果有函数体较长的，拆成小函数，但不要用 NotImplementedError 或 TODO 占位。**
