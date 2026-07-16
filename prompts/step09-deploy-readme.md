# Step 9: 部署配置 + README + 收尾

终局一步——让项目可部署、可展示、可面试。

## 已有基础设施

```
前端：
├── Dockerfile          # 已有（Step 2 骨架）
├── next.config.mjs     # 已有
├── .env.example        # 已有
└── package.json        # 已有

后端：
├── Dockerfile          # 已有（Step 2 骨架）
├── .env.example        # 已有
└── requirements.txt    # 已有

项目根：
├── docker-compose.yml  # 已有（Step 2 骨架）
├── .gitignore          # 已有
└── README.md           # 已有基础版（需重写）
```

---

## 第一部分：后端部署优化

### 1.1 Dockerfile 优化（backend/Dockerfile）

- 多阶段构建：builder 阶段装依赖，runtime 阶段只保留运行所需
- 基于 `python:3.11-slim`
- 非 root 用户运行
- 环境变量通过 `.env` 或运行时注入

### 1.2 Dockerfile 优化（frontend/Dockerfile）

- 基于 `node:20-alpine`
- 多阶段：deps → build → runner
- runner 阶段用 `node:20-alpine`，仅复制 `.next/standalone` + `.next/static` + `public`
- `next.config.mjs` 需开启 `output: "standalone"`

### 1.3 修改 next.config.mjs

```js
const nextConfig = {
  output: "standalone",
  // ... 已有配置保持不变
};
```

### 1.4 docker-compose.yml 优化

- 确保 `OPENAI_API_KEY` 从环境变量传入
- 添加 `restart: unless-stopped`
- 前端服务加健康检查（可选）

---

## 第二部分：CI/CD（可选加分项）

新建 `.github/workflows/deploy.yml`（GitHub Actions）：
- 仅作为模板，标注"使用前需配置 Vercel/Railway token"
- 包含 lint + 构建两步
- 部署步骤用注释标注（用户按需取消注释）

---

## 第三部分：README.md 重写

重写项目根目录 `README.md`，面向面试官和潜在使用者。结构如下：

### README 结构

```markdown
# AI 数据分析助手

> 可解释的 AI 数据分析助手 · 统计建模 + 自然语言洞察 + 可视化
> 求职作品集旗舰项目 — 统计学硕士 × AI 应用

## 在线体验（截图占位）

放置一张主要界面截图（报告中可截图后替换为真实截图链接）

## 核心差异

- **8 项自实现统计算法**：OLS / K-Means / Welch t / 卡方 / KS / Pearson / IQR+Z-score / RFM
- **全过程可解释**：每个分析标注方法 / 假设 / 解读 / 局限
- **AI 不黑盒**：LLM 仅翻译结构化结果，数字全部来自真实计算
- **电商行业模板**：RFM 用户分层 + 漏斗转化，开箱即用

## 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 前端 | Next.js + TailwindCSS + Recharts + Zustand | ... |
| 后端 | FastAPI + Pandas + NumPy + SciPy | ... |
| AI | OpenAI API（仅翻译，不计算） | ... |
| 存储 | Parquet + SQLite | ... |

## 自实现算法清单

| # | 方法 | 对照验证 |
|---|------|---------|
| 1 | OLS 回归 | vs statsmodels: β < 1e-6 |
| 2 | K-Means | vs sklearn: Iris ARI ≥ 0.7 |
| ... | ... | ... |

（完整 8 项列表，含验证结果）

## 快速开始

### 前置条件
- Docker & Docker Compose
- OpenAI API Key

### 本地运行

\`\`\`bash
# 1. 设置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 OPENAI_API_KEY

# 2. 启动
docker compose up --build

# 3. 访问
# 前端: http://localhost:3000
# 后端 API 文档: http://localhost:8000/docs
\`\`\`

### 不使用 Docker

\`\`\`bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端（新终端）
cd frontend
npm install
npm run dev
\`\`\`

## 项目结构

（目录树，标注关键文件）

## API 端点概览

（主要端点表格：datasets / analysis / modeling / templates / insight）

## 设计决策

### 为什么自实现而不全用 sklearn？
8 项算法手写是为了体现统计建模能力（面试可讲），分布 CDF/p 值调 SciPy 是合理边界（底层数学库），Isolation Forest 和 PCA 用 sklearn 是工程取舍（投入产出比）。

### 为什么 AI 不做计算？
LLM 幻觉不可控。本项目选择"LLM = 翻译器"架构：所有统计量由 NumPy/Pandas 产出，LLM 仅把结构化结果转成自然语言。好处：结论可溯源、数字可验证、模型可替换。

## License

MIT
```

---

## 第四部分：技术博客大纲

在项目根目录创建 `BLOG_OUTLINE.md`，内容是 1-2 篇技术博客的写作大纲（不要求完整文章，只需结构化大纲和关键段落）。这是为了方便后续撰写求职作品集的技术文章。

### 博客 1：《我是怎么在 AI 数据分析助手中自实现 8 项统计算法的》

大纲：
1. 背景：为什么统计学硕士的 AI 项目不能只是"调包"？
2. 自实现边界：核心计算 NumPy 手写 vs CDF/p 值 SciPy vs sklearn 照用
3. 每项算法的一句话原理 + 验证策略（对照结果）
4. 取舍案例：为什么 Isolation Forest 不手写？（投入产出比分析）
5. 可解释性设计：AnalysisResponse 三件套（data+explanation+meta）

### 博客 2：《LLM 在数据分析产品中的正确角色：翻译器而非算命师》

大纲：
1. 问题：让 LLM 直接分析数据的三重风险（幻觉、不可复现、黑盒）
2. 本项目的解法：结构化计算 → 注入 prompt → LLM 翻译
3. 降级策略：LLM 不可用时的结构化摘要
4. 可溯源设计：每个 AI 结论标注数据来源

---

## 第五部分：前端收尾

### 5.1 全局 loading/error 一致性检查

确保所有页面都有 loading 状态和 error 状态的展示（检查现有页面，缺失的补上）：
- `/upload` ✅
- `/dataset/[id]/overview` ✅
- `/dataset/[id]/clean` ✅
- `/dataset/[id]/stats` ✅
- `/dataset/[id]/model` ✅
- `/dataset/[id]/templates` ✅
- `/dataset/[id]/report` ✅
- `/methods` ✅ (static page, no loading needed)

### 5.2 404 页面

新建 `frontend/app/not-found.tsx`：友好的 404 页面，含返回首页链接。

### 5.3 全局错误边界

新建 `frontend/app/error.tsx`（Next.js error boundary）：捕获未预期的渲染错误，显示"出错了"提示 + 重试按钮。

---

## 需要输出的文件清单

1. `backend/Dockerfile` — 优化多阶段构建
2. `frontend/Dockerfile` — 优化多阶段构建
3. `frontend/next.config.mjs` — 添加 output: "standalone"
4. `docker-compose.yml` — 优化
5. `.github/workflows/deploy.yml` — 新建 CI/CD 模板
6. `README.md` — 完整重写
7. `BLOG_OUTLINE.md` — 新建，技术博客大纲
8. `frontend/app/not-found.tsx` — 新建 404 页
9. `frontend/app/error.tsx` — 新建 error boundary
10. `frontend/app/globals.css` — 检查是否需微调（响应式/暗色模式非必须）

---

## 验证清单

- [ ] `docker compose up --build` 启动成功，前端 3000 + 后端 8000 均可访问
- [ ] `README.md` 包含完整的快速开始指南
- [ ] 后端 Dockerfile 镜像大小合理（< 500MB）
- [ ] 前端 Dockerfile 构建成功
- [ ] 404 页面可访问（访问 `/nonexistent`）
- [ ] 全局 error 边界生效（在某个页面故意写错可触发）
- [ ] BLOG_OUTLINE.md 两篇大纲完整

---

**README 是面试官的入口，质量优先于数量。每个自实现算法都要写清楚对照验证结果——这是说服力的核心。**
