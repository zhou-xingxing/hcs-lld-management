from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, backup, change_logs, excel, lookup, network_plane_types, regions, stats, users
from app.services.auth import ensure_bootstrap_admin
from app.services.backup import ensure_backup_config
from app.services.backup_scheduler import backup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # startup: create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_bootstrap_admin(db)
        ensure_backup_config(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    backup_scheduler.start()
    try:
        yield
    finally:
        backup_scheduler.stop()


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
app.include_router(auth.router)
app.include_router(regions.router)
app.include_router(network_plane_types.router)
app.include_router(lookup.router)
app.include_router(excel.router)
app.include_router(change_logs.router)
app.include_router(stats.router)
app.include_router(backup.router)
app.include_router(users.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
