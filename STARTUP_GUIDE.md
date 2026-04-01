# Coffee Time Saver — 本地启动与测试指南

## 前置条件

| 工具 | 版本要求 | 验证命令 |
|------|----------|----------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker Desktop | 任意近期版本 | `docker --version` |

---

## 一、首次安装（只需执行一次）

### 1. 创建 Docker 容器

```bash
docker run -d --name cts-db -p 5432:5432 \
  -e POSTGRES_DB=coffee_time_saver \
  -e POSTGRES_USER=cts \
  -e POSTGRES_PASSWORD=cts_password \
  pgvector/pgvector:pg16

docker run -d --name cts-redis -p 6379:6379 redis:7-alpine
```

### 2. 初始化数据库

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python seed.py --demo
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

---

## 二、每次启动流程（开四个终端）

### 终端 1 — 数据库 & Redis

```bash
docker start cts-db cts-redis
```

验证：
```bash
docker ps
# 应看到 cts-db (5432) 和 cts-redis (6379) 状态为 Up
```

### 终端 2 — 后端（FastAPI）

```bash
cd backend
uvicorn main:app --reload
```

等待看到：`Application startup complete.`

验证：`curl http://localhost:8000/health` → `{"status":"ok"}`

### 终端 3 — Celery Worker

```bash
cd backend
celery -A tasks worker --loglevel=info --pool=solo
```

等待看到：`celery@... ready.`

> **必须从 `backend/` 目录运行。**`--pool=solo` 是 Windows 必须加的参数。
>
> Worker 负责：文件处理 Pipeline、邮件轮询、LLM 任务排序、每日 Briefing 生成。没有 Worker，上传文件后任务不会出现。

### 终端 4 — 前端（React + Vite）

```bash
cd frontend
npm run dev
```

等待看到：`Local: http://localhost:5173`

浏览器打开 **http://localhost:5173**，用 `pm@example.com / pm123456` 登录。

---

## 三、默认账号

| 角色 | 邮箱 | 密码 |
|------|------|------|
| Admin | admin@example.com | admin123456 |
| PM（演示） | pm@example.com | pm123456 |

> **演示请用 PM 账号登录。** 任务、文档、邮件都属于 PM 账号，Admin 账号下任务列表为空。

---

## 四、演示数据

### 注入干净演示数据（演示前执行）

```bash
cd backend
python seed_showcase.py
```

这会**完全清除**现有的任务/文档/邮件/项目，然后插入：
- 3 个项目（Metro Line 6 Extension、Office Relocation Q3、ERP System Upgrade）
- 10 个任务（7 个可见 open、2 个 completed、1 个 scheduled 隐藏）
- 3 个文档 stub（已处理，含正文，用于 Risk Analysis）
- 2 封邮件（1 已处理、1 未读）
- Daily Briefing 不预填，第一次打开 Dashboard 时由 LLM 实时生成

> 可以在每次演示前重新运行，安全幂等。

### 开发用数据（非演示场景）

```bash
cd backend
python seed_demo.py          # 插入带 [DEMO] 前缀的测试数据
python seed_demo.py --reset  # 先清除再重插
```

---

## 五、定时任务（Celery Beat，可选）

如果需要定时任务（每天自动生成 Briefing、自动重新排序任务），额外开一个终端：

```bash
cd backend
celery -A tasks beat --loglevel=info
```

| 任务 | 触发时间（UTC） |
|------|---------------|
| 生成所有用户的 Daily Briefing | 每天 06:00 |
| 重新对所有用户任务排序（LLM） | 每天 06:05 |
| 轮询邮箱 | 每 5 分钟 |

> 不启动 Beat，邮件轮询和定时重排不会自动触发，但手动操作（上传文件、创建任务）仍会实时触发 Worker。

---

## 六、配置 LLM（启用 AI 功能）

以下功能需要配好 LLM：Daily Briefing、Risk Analyzer、Task Sorting、文档任务提取。

### 操作步骤

1. 用 **admin@example.com** 登录
2. 进入 **Settings → LLM**
3. 添加一条配置（name 必须填 `primary`）：

| 字段 | OpenRouter 示例 | Ollama 本地示例 |
|------|----------------|-----------------|
| name | `primary` | `primary` |
| provider | `openai` | `ollama` |
| api_url | `https://openrouter.ai/api/v1` | `http://localhost:11434` |
| api_key | `sk-or-v1-xxx`（你的 key） | （留空） |
| model | `google/gemini-flash-3` | `qwen3:8b` |
| is_active | ✅ | ✅ |

> OpenRouter 兼容 OpenAI 协议，provider 选 `openai` 即可。

### `backend/.env` 策略开关

```env
TASK_SORTER_STRATEGY=llm        # hardcoded | llm
BRIEFING_STRATEGY=llm           # template | llm
EMAIL_TASK_STRATEGY=llm         # regex | llm
EMAIL_PROJECT_SUGGESTION=llm    # off | llm
TASK_PROJECT_ASSOCIATION=llm    # manual | llm
```

修改后重启后端生效。

---

## 七、邮件 Bot（可选）

邮件 Bot 是可选的。不配置 IMAP 时后端正常运行，只是不会自动拉取邮件。

如需启用，在 `backend/.env` 中配置：

```env
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=你的邮箱@gmail.com
IMAP_PASSWORD=你的应用密码
IMAP_OWNER_EMAIL=pm@example.com   # 邮件归属的用户
```

Gmail 需要开启"两步验证"并生成"应用专用密码"。

---

## 八、运行测试

### 单元测试（无需数据库）

```bash
cd backend
pytest tests/unit/ -v
```

### E2E 展示测试（需要完整栈运行中）

```bash
# 确保后端、Celery Worker、前端都已启动
python run_showcase_tests.py
# 结果写入 showcase_test_results.md
```

---

## 九、停止服务

```bash
# 后端 / Celery / 前端：在对应终端按 Ctrl+C

# 停止 Docker 容器（保留数据）
docker stop cts-db cts-redis

# 彻底删除容器和数据（慎用）
docker rm cts-db cts-redis
```

---

## 十、常见问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 前端登录显示 Network Error | 后端未启动，或 CORS 不匹配 | 确认后端在 8000 端口运行；`.env` 中 `ALLOWED_ORIGINS` 包含 `http://localhost:5173` |
| 组员电脑显示 Network Error | 前端 API 地址写死了 `localhost:8000`，在别人电脑上找不到后端 | 在 `frontend/.env.local` 中设置 `VITE_API_BASE_URL=http://你的IP:8000`，并在 `.env` 的 `ALLOWED_ORIGINS` 中加上组员的访问地址 |
| 上传文件后任务一直不出现 | Celery Worker 未运行 | 确认终端 3 已启动 Worker，且从 `backend/` 目录运行 |
| 后端启动报 `No module named 'xxx'` | 依赖未安装 | `pip install -r requirements.txt -r requirements-dev.txt` |
| 后端启动报 `could not connect to server` | PostgreSQL 容器未运行 | `docker start cts-db` |
| `alembic upgrade head` 报错 | DB 未就绪或 URL 错误 | 等容器完全启动后重试，检查 `.env` 中 `DATABASE_URL` |
| Tasks 页面为空（已登录） | 用了 admin 账号，任务属于 PM 账号 | 退出，改用 `pm@example.com` 登录 |
| Risk Analysis 一直转圈 | LLM 慢，正常耗时 60-130 秒 | 等待；可以切换到别的页面，结果在后台保存 |

---

## 十一、端口总览

| 服务 | 端口 |
|------|------|
| 前端 (Vite) | 5173 |
| 后端 (FastAPI) | 8000 |
| API 文档 | 8000/docs |
| PostgreSQL | 5432 |
| Redis | 6379 |
