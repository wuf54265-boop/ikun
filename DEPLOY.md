# 部署指南：Vercel（前端）+ Railway（后端）

> 目标：简历里放两个可点击链接，面试官点开即用的真实 demo。
> 前端 Vercel 免费，后端 Railway 有免费额度（足够 demo）。

---

## ✅ 部署前已本地验证（可放心照做）

- **后端（Railway 等价）**：注入 `PORT=8080` + 逗号分隔 `CORS_ORIGINS` 启动，`GET /health` → `{"status":"ok"}`，`/docs` 可访问。`Dockerfile` 的 `CMD` 读 `$PORT`（Railway 注入），本地无法起 Docker daemon，故用 venv 等价模拟已验证通过。
- **前端（Vercel 等价）**：`next build` 成功，生成 `standalone` 产物，所有路由编译通过。
- **关键修复**：`CORS_ORIGINS` 已支持**逗号分隔**（Railway/Vercel 控制台直接填 `a,b,c`，无需 JSON 数组）。早期版本填裸 URL 会导致后端启动即崩，现已修复（`backend/app/config.py`）。

---

## 前置条件

1. **代码进 GitHub**：本仓库已 `git init` 并提交，你只需关联远程并推送：
   ```bash
   git remote add origin https://github.com/<你的用户名>/ai-data-analysis-assistant.git
   git push -u origin main
   ```
   （默认分支名若为 `master` 请把上面 `main` 改成 `master`；`.github/workflows/deploy.yml` 的 CI 触发分支已涵盖二者。）
2. 注册 [Vercel](https://vercel.com) 与 [Railway](https://railway.app) 免费账号。

---

## 方式 A：Vercel 部署前端（免费）

1. 打开 https://vercel.com/new → **Import** 你的 GitHub 仓库。
2. 配置（Vercel 会自动识别 Next.js，但仍请核对）：
   - **Root Directory**：`frontend`（**必须选**，否则 Vercel 在仓库根目录找不到 `package.json`）
   - **Build Command**：`npm run build`（默认）
   - **Output**：自动（已配 `output: "standalone"`）
3. **Settings → Environment Variables** 添加：
   - `NEXT_PUBLIC_API_BASE` = `https://<你的Railway后端>.up.railway.app/api/v1`
   - ⚠️ `NEXT_PUBLIC_*` 变量在**构建时**内联进前端包，必须**部署前**就设好；之后修改需再次 **Redeploy**。
4. 点 **Deploy**。成功后域名形如 `https://<你的项目>.vercel.app`。

---

## 方式 B：Railway 部署后端（免费额度）

1. 打开 https://railway.app/new → **New Project → Deploy from GitHub repo**。
2. 选择本仓库，在 Service 设置里：
   - **Root Directory**：`backend`
   - **Builder**：Dockerfile（自动读取 `railway.toml`，含 `/health` 健康检查）
   - （无需手填端口，`PORT` 由 Railway 自动注入）
3. **Variables** 添加：
   - `CORS_ORIGINS` = `https://<你的Vercel>.vercel.app,http://localhost:3000`（**逗号分隔**，多个用半角逗号）
   - `ENV` = `production`
   - `OPENAI_API_KEY` = `sk-...`（**可选**；不填则 AI 报告自动降级，其余功能不受影响，适合纯演示）
4. Deploy 后拿到域名 `https://<随机名>.up.railway.app`。
5. 验证：浏览器打开 `https://<...>.up.railway.app/health` 应返回 `{"status":"ok"}`；`/docs` 是 Swagger 文档。

---

## 联调顺序（避免 CORS 报错）

1. **先部署 Railway（方式 B）** → 拿到 `xxx.up.railway.app`。
2. **再部署 Vercel（方式 A）**，把 `NEXT_PUBLIC_API_BASE` 填成上面的 Railway 地址。
3. Vercel 部署完拿到 `xxx.vercel.app` → 回到 Railway **Variables**，把 `CORS_ORIGINS` 改为 `https://xxx.vercel.app,http://localhost:3000` → Railway 自动重部署。
4. 完成。打开前端点「一键体验 Demo」即可走完整流程。

> 若想一次到位：可先临时把 Vercel 的 `NEXT_PUBLIC_API_BASE` 填占位、Railway 的 `CORS_ORIGINS` 先留 `http://localhost:3000`，两边部署完拿到真实域名后再互相回填并 Redeploy。

---

## 方式 C：GitHub Actions 自动部署（可选）

仓库已含 `.github/workflows/deploy.yml`：
- **CI 门禁（已启用）**：后端算法/集成测试 + 前端构建。
- **部署段（已写好但注释）**：需在你的仓库 **Settings → Secrets** 配置
  `VERCEL_TOKEN` / `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID` / `RAILWAY_TOKEN`
  后，取消 `deploy` job 注释，即可实现 push 即部署。

---

## 常见问题

| 现象 | 原因与解决 |
|------|-----------|
| 前端白屏 / 请求 404 | `NEXT_PUBLIC_API_BASE` 指向错误域名 → Vercel 改 Environment Variable 后 **Redeploy** |
| CORS 报错（跨域） | Railway 的 `CORS_ORIGINS` 未包含 Vercel 域名，或填成了 JSON 数组（应**逗号分隔裸 URL**） |
| AI 报告 503 | 没填 `OPENAI_API_KEY`，属**正常降级**；填 key 即恢复 |
| Railway 首次访问很慢 | 免费实例冷启动休眠，正常现象，过几秒即恢复 |
| 后端启动即崩 | 看 Railway 日志，多半是 `CORS_ORIGINS` 格式问题（现已支持逗号分隔，填 `a,b` 即可） |

---

## 本地预览（开发用）

```bash
# 后端
cd backend && source <你的venv>/Scripts/activate && uvicorn app.main:app --reload
# 前端
cd frontend && npm run dev
# 或双击仓库根目录的 start-all.cmd（Windows）
```

---

## 部署检查清单（上线前勾选）

- [ ] 代码已 `git push` 到 GitHub
- [ ] Railway 后端已部署，`/health` 返回 `{"status":"ok"}`
- [ ] Vercel 前端已部署，拿到 `*.vercel.app`
- [ ] Vercel 的 `NEXT_PUBLIC_API_BASE` = Railway 真实地址
- [ ] Railway 的 `CORS_ORIGINS` 含 Vercel 域名（逗号分隔）
- [ ] （可选）填了 `OPENAI_API_KEY`，AI 报告可用
- [ ] README 顶部「🌐 在线体验」已替换为真实链接
