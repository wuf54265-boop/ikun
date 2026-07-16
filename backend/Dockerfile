# ---- builder：仅用于安装依赖（含编译工具，最终不进入镜像）----
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装编译工具链（scipy / scikit-learn / pandas / pyarrow 均有 manylinux 预编译 wheel，
# 通常无需编译；此层仅作兜底，且不会进入 runtime 阶段）
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# 在独立 venv 中安装依赖，便于整体复制到 runtime 阶段
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- runtime：最小运行环境 ----
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR=/app/data \
    DB_PATH=/app/data/meta.db

# 非 root 用户运行
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

# 仅复制依赖 venv 与应用代码（构建工具链留在 builder 阶段）
COPY --from=builder /opt/venv /opt/venv
COPY . .

USER appuser

EXPOSE 8000

# Railway 等平台通过 $PORT 注入运行时端口；本地无 $PORT 时回退 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
