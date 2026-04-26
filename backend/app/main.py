from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import allocations, change_logs, excel, network_plane_types, regions, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: create tables
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="HCS LLD Management System",
    description="华为云Stack LLD 管理系统 - 网络平面IP地址规划管理",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(regions.router)
app.include_router(network_plane_types.router)
app.include_router(allocations.router)
app.include_router(excel.router)
app.include_router(change_logs.router)
app.include_router(stats.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
