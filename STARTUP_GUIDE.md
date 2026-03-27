# Coffee Time Saver — 本地启动与测试指南

## 前置条件

| 工具 | 版本要求 | 验证命令 |
|------|----------|----------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker Desktop | 任意近期版本 | `docker --version` |

---

## 一、启动流程（每次开发前执行）

### 第 1 步 — 启动数据库 & Redis 容器

```bash
docker start cts-db cts-redis
```

验证是否正常：
```bash
docker ps
# 应看到 cts-db (5432) 和 cts-redis (6379) 状态为 Up
```

> **首次使用？** 容器不存在时先创建：
> ```bash
> docker run -d --name cts-db -p 5432:5432 \
>   -e POSTGRES_DB=coffee_time_saver \
>   -e POSTGRES_USER=cts \
>   -e POSTGRES_PASSWORD=cts_password \
>   pgvector/pgvector:pg16
>
> docker run -d --name cts-redis -p 6379:6379 redis:7-alpine
> ```
> 然后初始化数据库（仅首次）：
> ```bash
> cd backend
> alembic upgrade head
> python seed.py --demo
> ```

---

### 第 2 步 — 启动后端（FastAPI）

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

验证：
```bash
curl http://localhost:8000/health
# 返回: {"status":"ok"}
```

后端日志在终端实时输出。API 文档访问：http://localhost:8000/docs

---

### 第 3 步 — 启动前端（React + Vite）

新开一个终端：

```bash
cd frontend
npm install        # 仅首次或 package.json 变动后需要
npm run dev
```

启动后访问：**http://localhost:5173**

---

## 二、默认账号

| 角色 | 邮箱 | 密码 |
|------|------|------|
| Admin | admin@example.com | admin123456 |
| PM (演示) | pm@example.com | pm123456 |

> 如果登录失败，确认数据库已运行并执行过 `python seed.py --demo`。

---

## 三、运行测试

### 单元测试（无需数据库）

```bash
cd backend
pytest tests/unit/ -v
# 当前：31 passed
```

### 集成测试（需要 DB + Redis 容器运行中）

```bash
cd backend
export TEST_DATABASE_URL=postgresql+asyncpg://cts:cts_password@localhost:5432/cts_test
pytest tests/unit/ tests/integration/ -v
```

---

## 四、停止服务

```bash
# 停止后端/前端：在对应终端按 Ctrl+C

# 停止 Docker 容器（保留数据）
docker stop cts-db cts-redis

# 彻底删除容器和数据（慎用）
docker rm cts-db cts-redis
```

---

## 五、注入演示数据

seed.py 只创建用户，不含业务数据。要看到完整的 Dashboard / Daily Briefing / Tasks，需要运行 demo seed：

```bash
cd backend
python seed_demo.py
```

这会注入：
- 3 个项目（Metro Line 6、Office Relocation、ERP Upgrade）
- 12 个任务（含 overdue、due today）
- 3 封邮件
- 1 个预写好的双语 Daily Briefing

> 如果数据乱了，用 `python seed_demo.py --reset` 清除重建。

用 **pm@example.com** 登录即可看到完整演示效果。

---

## 六、配置 LLM（可选，启用 AI 功能）

以下功能需要配好 LLM 才能工作：
- Daily Briefing（`BRIEFING_STRATEGY=llm` 时）
- Risk Analyzer（Tools 页面）
- Task Sorting（`TASK_SORTER_STRATEGY=llm` 时）

### 操作步骤

1. 用 **admin@example.com** 登录
2. 进入 **Settings → LLM**
3. 添加一条配置：

| 字段 | OpenRouter 示例 | Ollama 本地示例 |
|------|----------------|-----------------|
| name | `primary` | `primary` |
| provider | `openai` | `ollama` |
| api_url | `https://openrouter.ai/api/v1` | `http://localhost:11434` |
| api_key | `sk-or-v1-xxx`（你的 key） | （留空） |
| model | `google/gemini-2.5-flash` | `qwen3:8b` |
| is_active | ✅ | ✅ |

> OpenRouter 兼容 OpenAI 协议，provider 选 `openai` 即可。

### 后端 .env 策略开关

```env
# template = 不需要 LLM（默认），llm = 需要配好 LLM
BRIEFING_STRATEGY=template
TASK_SORTER_STRATEGY=hardcoded
STRUCTURER_STRATEGY=regex
```

改成 `llm` 后重启后端生效。Risk Analyzer 始终使用 LLM，不受这些开关影响。

---

## 七、常见问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 前端登录显示 Network Error | CORS 不匹配或后端未启动 | 确认后端在 8000 端口运行；`.env` 中 `ALLOWED_ORIGINS` 包含 `http://localhost:5173` |
| 后端启动报 `could not connect to server` | PostgreSQL 容器未运行 | `docker start cts-db` |
| `alembic upgrade head` 报错 | DB 未就绪或 URL 错误 | 等容器完全启动后重试，检查 `.env` 中 `DATABASE_URL` |
| 端口 5432/6379 被占用 | 本机已有同类服务 | `docker ps -a` 查看冲突容器并停止 |

---

## 八、端口总览

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 (Vite dev) | 5173 | http://localhost:5173 |
| 后端 (FastAPI) | 8000 | http://localhost:8000/docs |
| PostgreSQL | 5432 | cts-db 容器 |
| Redis | 6379 | cts-redis 容器 |
