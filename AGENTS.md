# AGENTS.md

This file provides guidance to Agents when working with code in this repository.

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

# 代码检查（ruff → black → mypy）
make lint
# 或: bash run_checks.sh

# 测试
make test
# 或: bash run_tests.sh
# 或: python -m pytest tests/ -v -k "region"
python -m pytest tests/test_regions.py::test_create_region -v

# 完整门禁（lint + test）
make check

# 种子数据
python seed.py

# pre-commit hooks（可选，提交时自动格式化）
# pre-commit install
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

### 前端

- **Composition API**（`<script setup>`）全项目统一
- **页面级状态**：每个 view 自行 fetch 数据。**Pinia 只存 UI 状态**（operator 名、侧边栏折叠），不要把数据获取放 Pinia
- **操作者追踪**：无认证系统。operator 通过 `X-Operator` header 传递（来源 localStorage，见 `stores/app.js`）。后端记录到变更日志
- **API 层** (`api/request.js`): Axios 实例，`baseURL=/api`，自动注入 `X-Operator`，全局错误 `ElMessage.error()`
- **Element Plus**：中文 locale，大量使用 `el-table`、`el-form`、`el-dialog`

### 测试

- 每个测试独立内存 SQLite（`StaticPool`），`conftest.py` 中 override `get_db`
- 当前共 30+ 个测试，5 个文件：health、regions、allocations、lookup、excel utils、plane_tree
- 前端无测试，CI 仅验证 `npm run build`

### CI/CD

- 见 `.github/workflows/ci.yml`，4 个并行 job：
  - `lint`：ruff → black --check → mypy
  - `test-backend`：pytest
  - `build-frontend`：npm install → npm run build
  - `build-and-push`：依赖前三个通过后，构建并推送 Docker 镜像到 GHCR

### 数据模型

更详细的设计说明见 `SYSTEM_DESIGN.md`。

## Python 编码规范

- **类型注解**：公共函数必须完整标注参数/返回类型。禁止滥用 `Any`，必要时可用 `# type: ignore[xxx]` 加说明。用 mypy 做静态检查。
- **导入**：绝对导入。按 标准库 / 第三方 / 应用 分三组，组内字母序，组间空行分隔。用 ruff（`I` 规则）自动排序。
- **命名**：变量/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE_CASE`，私有辅助/方法加 `_` 前缀。
- **错误处理**：禁止用 `None` 返回表示校验失败，禁止用 `ValueError` 表示业务异常。查找不到（not found）场景允许返回 `None`。业务违规（如 CIDR 重叠）用自定义业务异常类，Service 层 `raise`，Router 层 catch 并转 `HTTPException`。
- **异步**：网络 IO（HTTP 请求等）鼓励用 `async/await`；DB 操作视存储引擎而定，不强求。CPU 密集型操作用同步方式或交由 worker 处理。
- **格式**：行宽 ≤120。必须使用 black + ruff 格式化。
- **Docstring**：公共函数和类必须写 docstring，使用 Google 风格（`Args:` / `Returns:` / `Raises:`）。
- **Schema**：统一使用 Pydantic v2 `BaseModel`。Schema 仅用于 API 请求/响应定义，不承载业务逻辑。
- **分层**：严格遵守 `router → service` 两层核心结构。router 不写业务逻辑，service 通过 SQLAlchemy Session 直接访问数据，不强加 repository 层。
- **工程规范**：禁止 `print()`，使用 `logging` 模块。业务逻辑必须写 pytest 测试。CI 中必须通过 lint、type check、test 三步。
