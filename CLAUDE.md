# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

HCS LLD 管理系统 —— 管理云平台 Region 网络平面 IP 地址分配的 Web 应用，替代 Excel 手动管理。UI 为中文（zh-CN）。

技术栈：Python 3.12 + FastAPI + SQLAlchemy + SQLite（后端），Vue 3 + Vite + Element Plus（前端）。

## 常用命令

### 后端（`backend/`）

```bash
cd backend

# 开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 或: bash start.sh

# 数据库迁移
alembic upgrade head

# 测试
python -m pytest tests/ -v
python -m pytest tests/test_regions.py -v
python -m pytest tests/test_regions.py::test_create_region -v
# 或: bash run_tests.sh

# 种子数据
python seed.py
```

首次运行：
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .
alembic upgrade head
```

### 前端（`frontend/`）

```bash
cd frontend
npm install
npm run dev         # http://localhost:5173
npm run build
```

Vite dev server 代理 `/api` → `http://localhost:8000`。

### Docker

```bash
docker compose up -d                    # 完整栈
docker compose logs -f                  # 查看日志
```

## 代码架构

### 后端三层结构

```
routers/  →  services/  →  models/
```

- **Routers** (`app/routers/`): FastAPI `APIRouter`，处理 HTTP，调用 services
- **Services** (`app/services/`): 业务逻辑，直接操作 models
- **Models** (`app/models/`): SQLAlchemy ORM，UUID v4 主键（`String(36)`）
- **Schemas** (`app/schemas/`): Pydantic 模型

关键模式（不能从单文件看出来的）：

- **显式审计日志**：Service 在 mutate 后**手动**调用 `log_change()`，不用 SQLAlchemy events。这是有意设计，更易控、可测试。
- **CIDR 重叠检测**：在 Python 内存用 `ipaddress` 模块完成（`app/utils/ip_utils.py`）。SQLite 无原生 CIDR 类型，需加载全表到内存比较。MVP 数据量下性能足够。
- **反规范化**：`IPAllocation` 直接存 `region_id`，避免频繁 JOIN。应用层保证 `(region_id, plane_type_id)` 对应有效的 `RegionNetworkPlane`。
- **导入两阶段**：`preview` → `confirm`。预览数据在内存缓存（TTL 30min，`IMPORT_TTL_MINUTES`）。见 `app/services/excel.py`。
- **启动时建表**：`main.py` lifespan 调用 `Base.metadata.create_all()`，Alembic 仍管迁移，但新部署无需手动建表。
- **Alembic 配置**：`render_as_batch=True`（`alembic/env.py`），兼容 SQLite 的 ALTER TABLE 限制。

### 测试

- 每个测试独立内存 SQLite（`StaticPool`），`conftest.py` 中 override `get_db`
- 共 23 个测试，5 个文件：health、regions、allocations、lookup、excel utils
- 前端无测试，CI 仅验证 `npm run build`

### 前端

- **Composition API**（`<script setup>`）全项目统一
- **页面级状态**：每个 view 自行 fetch 数据。**Pinia 只存 UI 状态**（operator 名、侧边栏折叠），不要把数据获取放 Pinia
- **操作者追踪**：无认证系统。operator 通过 `X-Operator` header 传递（来源 localStorage，见 `stores/app.js`）。后端记录到变更日志
- **API 层** (`api/request.js`): Axios 实例，`baseURL=/api`，自动注入 `X-Operator`，全局错误 `ElMessage.error()`
- **Element Plus**：中文 locale，大量使用 `el-table`、`el-form`、`el-dialog`

### 数据模型

5 个实体：Region、NetworkPlaneType、RegionNetworkPlane、IPAllocation、ChangeLog。

关系：Region 1:N RegionNetworkPlane N:1 NetworkPlaneType。Region 1:N IPAllocation。NetworkPlaneType 1:N IPAllocation。

更详细的设计说明见 `SYSTEM_DESIGN.md`。
