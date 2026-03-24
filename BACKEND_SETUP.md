# Coffee Time Saver — Backend Setup Guide

## 前提条件

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.12 | 后端运行时 |
| Docker | 任意 | 用于启动 PostgreSQL + Redis（可用本地安装替代） |

---

## 层级 1 — 只跑单元测试（无需数据库）

适合快速验证纯逻辑模块（chunker、parser、sorter、auth/JWT 等）。

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit/
```

不需要数据库，不需要 Redis，不需要 `.env`。

---

## 层级 2 — 本地运行 API 服务

### 1. 启动数据库和 Redis

```bash
# PostgreSQL 16 + pgvector
docker run -d --name cts-db -p 5432:5432 \
  -e POSTGRES_DB=coffee_time_saver \
  -e POSTGRES_USER=cts \
  -e POSTGRES_PASSWORD=cts_password \
  pgvector/pgvector:pg16

# Redis
docker run -d --name cts-redis -p 6379:6379 redis:7-alpine
```

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少修改以下两项（其余保持默认即可本地运行）：

```env
# 本地运行时将 @db 改为 @localhost，@redis 改为 localhost
DATABASE_URL=postgresql+asyncpg://cts:cts_password@localhost:5432/coffee_time_saver
REDIS_URL=redis://localhost:6379/0

# 生产环境必须替换为随机长字符串
JWT_SECRET=change-me-in-production
```

### 4. 运行数据库迁移

```bash
alembic upgrade head
```

创建全部 14 张表、启用 pgvector 扩展、写入初始角色和权限数据。

### 5. 创建初始用户

```bash
# 只创建 admin 账号（admin@example.com / admin123456）
python seed.py

# 同时创建演示 PM 账号（pm@example.com / pm123456）
python seed.py --demo

# 自定义账号
python seed.py --email you@company.com --password yourpassword --name "Your Name" --demo
```

脚本可重复执行，已存在的用户会被跳过。

### 6. 启动 API 服务

```bash
uvicorn main:app --reload
```

服务启动后访问：
- API：`http://localhost:8000`
- 交互文档（Swagger）：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

---

## 层级 3 — 完整运行（含异步任务）

文件解析、每日简报生成、邮件轮询等功能通过 Celery 异步执行，需要额外启动 worker。

```bash
# 在另一个终端（与 uvicorn 并行运行）
cd backend
celery -A tasks.celery_app worker --loglevel=info

# 定时任务调度（邮件轮询等），可选
celery -A tasks.celery_app beat --loglevel=info
```

> 没有 Celery worker 时，API 仍可正常响应，但上传的文件不会被处理，每日简报不会自动生成。

---

## 层级 4 — 全栈 Docker Compose

```bash
# 启动全部 6 个服务（frontend、backend、db、redis、celery-worker、celery-beat）
cd backend
docker-compose up -d

# 首次启动后跑迁移
docker-compose exec backend alembic upgrade head

# 创建初始用户
docker-compose exec backend python seed.py --demo
```

---

## 集成测试

需要 PostgreSQL 容器运行中（层级 2 第 1 步）。

```bash
cd backend
export TEST_DATABASE_URL=postgresql+asyncpg://cts:cts_password@localhost:5432/cts_test
pytest tests/unit/ tests/integration/ -v
```

---

## 默认账号

| 角色 | 邮箱 | 密码 | 创建方式 |
|------|------|------|----------|
| Admin | admin@example.com | admin123456 | `python seed.py` |
| PM（演示） | pm@example.com | pm123456 | `python seed.py --demo` |

---

## 常见问题

**`alembic upgrade head` 报错 `pgvector extension not found`**
→ 确认使用的是 `pgvector/pgvector:pg16` 镜像，而不是普通 `postgres:16`。

**`bcrypt` 相关导入错误**
→ 确认安装的是 `bcrypt==4.2.1`，项目已移除 `passlib` 依赖。

**连接被拒绝（Connection refused）**
→ 检查 `.env` 中的 `DATABASE_URL` 和 `REDIS_URL` 是否将 `@db`、`@redis` 改为了 `@localhost`（docker-compose 内部主机名只在容器内有效）。