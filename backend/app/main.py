"""FastAPI 应用入口：装配路由、CORS、生命周期（初始化 SQLite）。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    cleaning,
    datasets,
    insight,
    modeling,
    profiling,
    stats,
    templates,
    viz,
)
from app.store.db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化元数据数据库（幂等）
    init_db(settings.db_path)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由装配：所有端点挂在 /api/v1 下
for router in (datasets, profiling, cleaning, stats, modeling, templates, insight, viz):
    app.include_router(router.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok"}
