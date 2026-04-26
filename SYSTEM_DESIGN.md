# HCS LLD 管理系统 - 架构设计文档

## 1. 项目背景

HCS（华为云Stack）是企业内部部署的私有云平台。LLD（Low Level Design）是部署 HCS 所需的详细设计文档，通常以 Excel 文件形式记录部署云平台所需的各类网络平面（Network Plane）地址段规划。随着管理的云平台数量增多，传统的本地 Excel 管理方式存在以下问题：

- 多个 Region 的数据分散在多个文件中，难以统一查询
- 无法快速检查某 IP 段是否已被分配
- 数据变更无版本追溯能力
- 多人协作困难

本系统旨在提供一个 Web 管理平台来解决上述问题。

## 2. 核心需求

| 需求 | 说明 |
|---|---|
| Region 管理 | 查询、创建、更新、删除云平台 Region |
| 网络平面自定义 | 可自定义网络平面类型（如管理平面、业务平面、存储平面等），每个 Region 可独立启用/禁用 |
| IP 分配管理 | 管理每个 Region 下各网络平面的 IP 地址段（CIDR），含 VLAN ID、网关、用途、状态等元数据 |
| IP 查重 | 给定 IP 地址或 CIDR 地址段，快速检查是否已被分配，返回所属 Region 和网络平面 |
| Excel 导入 | 按模板格式上传 Excel，支持预览验证后批量导入 |
| Excel 导出 | 按 Region/网络平面过滤导出为 Excel |
| 变更追溯 | 所有数据操作（创建/更新/删除/导入）自动记录变更日志，可查询操作者、时间、变更内容 |

## 3. 技术选型

| 层级 | 技术 | 版本 | 选型理由 |
|---|---|---|---|
| 后端框架 | Python FastAPI | 0.115+ | 高性能异步框架，自动生成 OpenAPI 文档，Pydantic 校验 |
| ORM | SQLAlchemy | 2.0+ | 成熟可靠，支持迁移工具 Alembic |
| 数据库 | SQLite | 3.x | 零配置，单文件存储，适合 MVP 阶段 |
| 数据库迁移 | Alembic | 1.14+ | SQLAlchemy 官方迁移工具 |
| Excel 处理 | openpyxl | 3.1+ | 纯 Python Excel 读写，无系统依赖 |
| IP 处理 | ipaddress | Python 内置 | 标准库，CIDR 解析与重叠检测 |
| 前端框架 | Vue 3 | 3.5+ | Composition API，体积小，生态丰富 |
| 前端构建 | Vite | 5.4+ | 极速 HMR，开箱即用 |
| UI 组件库 | Element Plus | 2.8+ | 中文友好，表格/表单/对话框组件丰富 |
| 状态管理 | Pinia | 2.2+ | Vue 3 官方推荐状态管理 |
| HTTP 客户端 | Axios | 1.7+ | 拦截器、请求/响应转换 |
| 前后端通信 | RESTful API | - | 简单通用，便于调试 |

## 4. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vite)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 仪表盘   │  │ 区域管理  │  │网络平面  │  │IP查找    │ │
│  │          │  │          │  │类型管理  │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │导入/导出 │  │变更历史  │  │区域详情  │               │
│  │          │  │          │  │(IP分配)  │               │
│  └──────────┘  └──────────┘  └──────────┘               │
│                    │                                     │
│               Axios / REST API                           │
│              (Vite Proxy: 5173 → 8000)                    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 后端 (FastAPI)                            │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Routers (API 路由层)                               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │  │
│  │  │ regions  │ │ plane-   │ │allocations│ │excel  │ │  │
│  │  │          │ │ types    │ │+lookup   │ │       │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────┘ │  │
│  │  ┌──────────┐ ┌──────────┐                         │  │
│  │  │change-   │ │ stats    │                         │  │
│  │  │ logs     │ │          │                         │  │
│  │  └──────────┘ └──────────┘                         │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Services (业务逻辑层)                               │  │
│  │  region/plane_type/allocation/excel/change_log      │  │
│  │  - CIDR 重叠检测 (Python ipaddress)                  │  │
│  │  - 变更日志自动记录                                   │  │
│  │  - Excel 预览缓存 (30分钟 TTL)                       │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Models (SQLAlchemy ORM) <═══> SQLite (hcs_lld.db)  │  │
│  │  Region / NetworkPlaneType / RegionNetworkPlane /   │  │
│  │  IPAllocation / ChangeLog                           │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 4.1 后端分层架构

后端采用经典的三层架构：

1. **Router 层** - API 端点定义，请求参数解析，响应序列化。依赖 `get_db` 获取数据库会话，`get_operator` 从请求头 `X-Operator` 提取操作者。
2. **Service 层** - 核心业务逻辑，包括 CIDR 重叠检测、变更日志记录、Excel 解析验证。Router 层调用 Service 层，Service 层操作 Model 层。
3. **Model 层** - SQLAlchemy ORM 模型，定义数据表结构和关系。通过 Alembic 管理数据库迁移。

### 4.2 前端组件架构

前端采用 Vue 3 Composition API + Vue Router 组织页面：

- **App.vue** - 根组件，仅包含 `<router-view />`
- **AppLayout.vue** - 布局组件，包含侧边栏导航 + 顶栏（面包屑 + 操作者输入）+ 内容区
- **views/** - 7 个页面组件，每个对应一个路由
- **api/** - Axios 请求封装模块，按业务领域拆分
- **stores/** - Pinia 状态管理（仅存储操作者名等 UI 状态）
- **router/** - 路由配置，懒加载页面组件

## 5. 数据模型设计

### 5.1 实体关系图

```
┌──────────────┐       ┌─────────────────────┐       ┌──────────────────┐
│    Region    │       │  RegionNetworkPlane │       │ NetworkPlaneType │
├──────────────┤       ├─────────────────────┤       ├──────────────────┤
│ id (PK)      │──1:N──│ id (PK)             │N:1────│ id (PK)          │
│ name (UNIQUE)│       │ region_id (FK)      │       │ name (UNIQUE)    │
│ description  │       │ plane_type_id (FK)  │       │ description      │
│ created_at   │       │ UNIQUE(r_id,pt_id)  │       │ created_at       │
│ updated_at   │       │ created_at          │       └──────────────────┘
└──────┬───────┘       └─────────────────────┘
       │1:N
       │
       │                ┌──────────────────┐
       │                │   IPAllocation   │
       └────────────────├──────────────────┤
                        │ id (PK)          │
                        │ region_id (FK)   │
                        │ plane_type_id(FK)│
                        │ ip_range (CIDR)  │
                        │ vlan_id          │
                        │ gateway          │
                        │ subnet_mask      │
                        │ purpose          │
                        │ status           │
                        │ created_at       │
                        │ updated_at       │
                        └──────────────────┘

┌─────────────────────────────┐
│        ChangeLog            │
├─────────────────────────────┤
│ id (PK)                     │
│ entity_type                 │  ← 表名: region/ip_allocation/...
│ entity_id                   │
│ action                      │  ← create/update/delete/import
│ field_name                  │  ← 变更的字段名 (update时)
│ old_value / new_value       │  ← 变更前后的值
│ operator                    │  ← 操作者
│ comment                     │
│ created_at                  │
└─────────────────────────────┘
```

### 5.2 核心表设计

#### regions

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String(36) UUID | PK | UUID v4 |
| name | String(100) | NOT NULL, UNIQUE, INDEX | 如 "HCS华北-北京" |
| description | Text | NULLABLE | 自由文本 |
| created_at | DateTime | NOT NULL | 创建时间 |
| updated_at | DateTime | NOT NULL, onupdate | 更新时间 |

#### network_plane_types

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String(36) UUID | PK | UUID v4 |
| name | String(100) | NOT NULL, UNIQUE, INDEX | 如 "管理平面" |
| description | Text | NULLABLE | 描述 |
| created_at | DateTime | NOT NULL | 创建时间 |

全局目录表，所有 Region 共享。

#### region_network_planes

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String(36) UUID | PK | UUID v4 |
| region_id | String(36) | FK -> regions.id, CASCADE | 所属 Region |
| plane_type_id | String(36) | FK -> network_plane_types.id, CASCADE | 启用的平面类型 |
| | | UNIQUE(region_id, plane_type_id) | 防止重复启用 |

多对多关联表，表示某个 Region 启用了哪些网络平面。

#### ip_allocations

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String(36) UUID | PK | UUID v4 |
| region_id | String(36) | FK -> regions.id, CASCADE, INDEX | 所属 Region（反范式化） |
| plane_type_id | String(36) | FK -> network_plane_types.id, CASCADE, INDEX | 所属网络平面 |
| ip_range | String(43) | NOT NULL | CIDR 表示法，如 "10.0.0.0/24" |
| vlan_id | Integer | NULLABLE | VLAN 标识 |
| gateway | String(39) | NULLABLE | 网关地址 |
| subnet_mask | String(15) | NULLABLE | 子网掩码 |
| purpose | Text | NULLABLE | 用途描述 |
| status | String(20) | default='active' | active/reserved/deprecated |
| created_at | DateTime | NOT NULL | 创建时间 |
| updated_at | DateTime | NOT NULL, onupdate | 更新时间 |

**设计决策**：`region_id` 在此表反范式化存储。虽然 `ip_range` 通过 `plane_type_id` 已间接关联 Region，但直接存储 `region_id` 可避免频繁 JOIN，加速 CIDR 查找。应用层保证 `(region_id, plane_type_id)` 必须是有效的 `RegionNetworkPlane`。

#### change_logs

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String(36) UUID | PK | UUID v4 |
| entity_type | String(50) | NOT NULL, INDEX | 实体类型 |
| entity_id | String(36) | NOT NULL, INDEX | 实体 ID |
| action | String(20) | NOT NULL | create/update/delete/import |
| field_name | String(100) | NULLABLE | update 时记录字段名 |
| old_value | Text | NULLABLE | JSON 或纯文本 |
| new_value | Text | NULLABLE | JSON 或纯文本 |
| operator | String(100) | NOT NULL | 操作者 |
| comment | Text | NULLABLE | 备注 |
| created_at | DateTime | NOT NULL, INDEX | 创建时间 |

**设计决策**：显式服务层变更日志记录，而非 SQLAlchemy 事件监听。Service 在每次 mutate 操作后调用 `log_change()`，更可控、可测试。

## 6. API 设计

### 6.1 API 端点总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET/POST | `/api/regions` | 列表/创建 Region |
| GET/PUT/DELETE | `/api/regions/{id}` | Region 详情/更新/删除 |
| GET/POST/DELETE | `/api/regions/{id}/planes` | 启用的网络平面管理 |
| GET/POST | `/api/regions/{region_id}/allocations` | IP 分配列表/创建 |
| GET/PUT/DELETE | `/api/allocations/{id}` | IP 分配详情/更新/删除 |
| GET/POST | `/api/network-plane-types` | 列表/创建网络平面类型 |
| GET/PUT/DELETE | `/api/network-plane-types/{id}` | 类型详情/更新/删除 |
| GET | `/api/lookup?q={ip_or_cidr}&exact=true` | IP/CIDR 查重 |
| GET | `/api/excel/template` | 下载导入模板 |
| POST | `/api/excel/import/preview` | 上传 Excel 预览 |
| POST | `/api/excel/import/confirm` | 确认导入 |
| GET | `/api/excel/export` | 导出 Excel |
| GET | `/api/change-logs` | 变更日志查询 |
| GET | `/api/stats` | 统计数据 |

### 6.2 关键接口详情

#### IP 查重 (GET /api/lookup)

查询参数：`q` (IP/CIDR), `exact` (bool)

处理逻辑：
1. 先尝试解析为单 IP（`parse_ip`），若成功则查找包含该 IP 的所有分配
2. 若单 IP 解析失败，尝试解析为 CIDR（`parse_cidr`）
3. `exact=true` 时，CIDR 精确匹配；`exact=false` 时，CIDR 重叠匹配
4. 在 Python 内存中使用 `ipaddress` 模块进行包含/重叠检测（SQLite 无原生 CIDR 类型）

#### Excel 导入（两阶段）

```
第一阶段: POST /api/excel/import/preview
  → 上传 Excel → 解析验证 → 返回预览数据 + preview_id
  → 预览数据在内存缓存 30 分钟

第二阶段: POST /api/excel/import/confirm
  → 传入 preview_id + operator
  → 批量插入有效行，逐行检查 CIDR 重叠
  → 逐条记录变更日志
```

### 6.3 错误处理

所有 API 错误返回一致格式：`{ "detail": "错误描述" }`

| 场景 | HTTP 状态码 |
|---|---|
| 实体不存在 | 404 |
| 参数校验失败 | 422 |
| 资源冲突（重复名称/重叠 CIDR） | 409 |
| 服务器内部错误 | 500 |

### 6.4 操作者跟踪

MVP 未实现认证系统。操作者通过请求头 `X-Operator` 传递，前端在本地存储持久化。

## 7. 关键技术决策

### 7.1 反范式化 region_id

**决策**：在 `IPAllocation` 表直接存储 `region_id` 和 `plane_type_id`。

**理由**：标准 CIDR 重叠查询需要 `SELECT * FROM ip_allocations WHERE region_id=? AND plane_type_id=?`，然后在 Python 中进行重叠过滤。直接存储 Region 引用避免了 JOIN 操作。MVP 数据量（< 1000 条）下 Python 端重叠过滤性能足够。

### 7.2 Python 端 CIDR 重叠检测

**决策**：使用 Python `ipaddress` 标准库进行 CIDR 解析和重叠检测，而非编写原始 SQL。

**理由**：SQLite 无原生 CIDR 数据类型。`ipaddress.IPv4Network.overlaps()` 提供了正确的语义。MVP 数据量下内存扫描性能绰绰有余。

### 7.3 服务层变更日志

**决策**：Service 层显式调用 `log_change()`，而非 SQLAlchemy 事件监听器。

**理由**：事件监听器需要额外的 `session.info` 传递操作者上下文，且隐含行为难以调试。Service 层方式是显式的、可单元测试的。

### 7.4 UUID 主键

**决策**：所有表使用 UUID v4 主键，存储为 `String(36)`。

**理由**：UUID 防止 ID 枚举攻击，便于未来数据迁移/合并（分布式无冲突）。字符串格式在 API 响应和日志中可读性好。

### 7.5 两阶段 Excel 导入

**决策**：预览（解析验证）→ 确认（批量写入）两阶段。

**理由**：预览步骤让用户在提交前检查解析结果和验证错误。确认时只需传入 preview_id，避免大数据量重新传输。预览缓存 30 分钟防止内存无限增长。

### 7.6 前端本地状态管理

**决策**：每个页面独立 fetch 数据，Pinia 仅存储 UI 状态（操作者名、侧边栏状态）。

**理由**：共享实体状态引入一致性挑战（跨页面数据同步），没有 WebSocket 难以保持同步。独立 fetch 更简单、正确。

## 8. 前端路由设计

| 路径 | 页面组件 | 说明 |
|---|---|---|
| `/dashboard` | Dashboard.vue | 统计概览仪表盘 |
| `/regions` | Regions.vue | 区域列表 CRUD |
| `/regions/:id` | RegionDetail.vue | 区域详情 + 网络平面管理 + IP 分配 CRUD |
| `/plane-types` | PlaneTypes.vue | 网络平面类型 CRUD |
| `/lookup` | Lookup.vue | IP/CIDR 查重搜索 |
| `/import-export` | ImportExport.vue | Excel 导入/导出（Tab 页切换） |
| `/change-logs` | ChangeLogs.vue | 变更历史筛选查询 |

## 9. 部署说明

### 环境要求

- 开发环境：Python >= 3.12, Node.js >= 18
- Docker 部署：Docker >= 24.0, Docker Compose >= 2.0

### Docker 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Host                           │
│                                                           │
│  ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │  frontend (Nginx)   │    │  backend (uvicorn)       │  │
│  │  ┌───────────────┐  │    │  ┌───────────────────┐  │  │
│  │  │ Vue 3 SPA     │  │    │  │ FastAPI App       │  │  │
│  │  │ (静态文件)     │  │    │  └───────────────────┘  │  │
│  │  └───────────────┘  │    │  ┌───────────────────┐  │  │
│  │  ┌───────────────┐  │    │  │ SQLite            │  │  │
│  │  │ API 代理      │──┼────┼──│ (/app/data/*.db)  │  │  │
│  │  │ /api → backend│  │    │  └───────┬───────────┘  │  │
│  │  └───────────────┘  │    │          │               │  │
│  └─────────────────────┘    └──────────┼────────────────┘  │
│                                        │                   │
│                               ┌────────┴────────┐          │
│                               │  Volume / Bind   │          │
│                               │  /app/data       │          │
│                               └─────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

### Docker 部署

#### 方式一：Docker Compose（一键部署）

```bash
docker compose up -d
docker compose logs -f
```

各服务配置：

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=sqlite:////app/data/hcs_lld.db
    volumes:
      - hcs-lld-data:/app/data    # 数据库持久化
    healthcheck:
      test: curl http://localhost:8000/api/health

  frontend:
    build:
      context: ./frontend
      args:
        - VITE_API_BASE_URL=/api  # 构建时 API 路径
    ports: ["80:80"]
    environment:
      - BACKEND_URL=http://backend:8000  # 运行时后端地址
    depends_on:
      backend:
        condition: service_healthy
```

#### 方式二：分别构建部署

```bash
# 后端
docker build -t hcs-lld-backend -f backend/Dockerfile backend/
docker run -d --name hcs-lld-backend -p 8000:8000 \
  -v hcs-lld-data:/app/data hcs-lld-backend

# 前端
docker build -t hcs-lld-frontend \
  --build-arg VITE_API_BASE_URL=/api \
  -f frontend/Dockerfile frontend/
docker run -d --name hcs-lld-frontend -p 80:80 \
  -e BACKEND_URL=http://你的后端IP:8000 hcs-lld-frontend
```

### Docker 设计要点

1. **多阶段构建**：builder 阶段安装依赖和编译，runtime 阶段仅包含运行所需，减小镜像体积
2. **数据库持久化**：后端通过 `DATABASE_URL` 将数据库路径指向 `/app/data/`，通过 Docker volume 或 bind mount 持久化
3. **前端代理**：Nginx 在容器启动时通过 `BACKEND_URL` 环境变量（envsubst）配置后端代理地址，支持运行时配置无需重新构建
4. **健康检查**：后端配置 `HEALTHCHECK` 确保服务可用后才接受流量
5. **构建缓存**：`requirements.txt` 和 `package.json` 在源码之前复制，利用 Docker 层缓存加速重复构建

## 10. CI/CD 设计

### 10.1 流水线架构

```
                        代码推送 (git push)
                              │
                    ┌─────────▼─────────┐
                    │   GitHub Actions   │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
     ┌────────▼──────┐ ┌─────▼──────┐ ┌──────▼─────────┐
     │     lint      │ │test-backend│ │build-frontend   │
     │               │ │            │ │                 │
     │  ruff 检查     │ │ pytest 37 项│ │ npm build       │
     │  black --check │ │ SQLite 内存 │ │ 编译检查         │
     │  mypy 检查     │ │            │ │                 │
     └───────┬───────┘ └──────┬─────┘ └──────┬─────────┘
              │               │               │
              └───────┬───────┘               │
                      │                       │
              ┌───────▼───────┐               │
              │ build-and-push│◄──────────────┘
              │               │
              │ Docker buildx │
              │ ghcr.io 推送  │
              └───────────────┘
```

### 10.2 触发规则

| 事件 | 触发行为 |
|---|---|
| PR 提交/更新到 `main` | `lint` + `test-backend` + `build-frontend`（验证不推送） |
| 推送 `main` 分支 | 全部测试 + Docker 构建并推送 latest + SHA 标签 |
| 推送 `v*` 标签 | 全部测试 + Docker 构建并推送 version + latest + SHA 标签 |

### 10.3 工作流定义

四个 Job 按需串联：

1. **lint** — ruff 检查 + black --check + mypy 类型检查
   - pip 缓存加速重复运行
   - mypy 非阻断（允许类型问题但不阻断流程）

2. **test-backend** — Python 3.12, 安装依赖后执行 `pytest tests/ -v`
   - pip 缓存加速重复运行
   - 每个测试用例独立内存 SQLite 数据库，互不干扰

3. **build-frontend** — Node 20, `npm install && npm run build`
   - 仅验证编译是否通过
   - MVP 阶段前端逻辑简单，不编写单元测试

4. **build-and-push** — 依赖 lint + test-backend + build-frontend 三个 Job 成功
   - 使用 Docker Buildx 构建多平台兼容镜像
   - 登录 ghcr.io（使用 GITHUB_TOKEN，无需额外 secrets）
   - Matrix 策略并行构建 backend 和 frontend 镜像
   - 镜像缓存（GitHub Actions Cache）加速重复构建

### 10.4 镜像标签策略

| 标签 | 生成条件 | 示例 |
|---|---|---|
| `latest` | 推送 main 分支时 | `ghcr.io/owner/hcs-lld-backend:latest` |
| `sha-{short}` | 推送 main 分支时 | `ghcr.io/owner/hcs-lld-backend:sha-a1b2c3d` |
| `{version}` | 推送 v* 标签时 | `ghcr.io/owner/hcs-lld-backend:1.0.0` |

### 10.5 测试策略

- **数据库隔离**：每个测试用例使用独立的内存 SQLite（`sqlite://` + `StaticPool`），`Base.metadata.create_all()` 在每个 fixture 中独立建表，互不污染
- **依赖注入覆盖**：通过 `app.dependency_overrides[get_db]` 将数据库会话替换为测试用内存数据库会话
- **无 E2E 测试**：MVP 阶段只做后端 API 测试 + 前端 build 验证。E2E 测试维护成本高于当前收益

### 10.6 关键决策

1. **GITHUB_TOKEN 无需额外配置**：GitHub Actions 内置 token 自动有权限推送 ghcr.io 至当前仓库
2. **Matrix 构建**：backend 和 frontend 使用同一 workflow 的 matrix 策略并行构建，减少 CI 总耗时
3. **Docker 层缓存**：使用 `type=gha` 缓存模式，利用 GitHub Actions Cache 加速镜像构建



