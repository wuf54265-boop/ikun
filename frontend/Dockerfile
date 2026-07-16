# ---- deps：仅安装依赖 ----
FROM node:20-alpine AS deps

WORKDIR /app

# 无 lockfile 时 npm install 会按 package.json 解析；如需可复现构建请先提交 package-lock.json
COPY package.json ./
RUN npm install

# ---- builder：构建 standalone 产物 ----
FROM node:20-alpine AS builder

WORKDIR /app

# 复制已安装的依赖（含 node_modules）
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* 在构建期内联到前端包中！
# 默认值指向宿主机 localhost:8000（compose 已把后端端口发布到宿主机，浏览器端可直连）。
# 部署到生产时通过 build arg 覆盖为真实域名（如 https://api.example.com/api/v1）。
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE

RUN npm run build

# ---- runner：最小运行环境 ----
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# 复制 standalone 服务器、静态资源与 public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

# standalone 服务器入口（next build 生成于 .next/standalone/server.js）
CMD ["node", "server.js"]
