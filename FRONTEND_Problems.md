# FRONTEND Problems

## Context
- Check date: 2026-03-24
- Scope: frontend integration check against the current backend
- Constraint followed: no code changes were made during this check

## Confirmed Problems

### 1. `POST /api/tasks` returns `500` during task creation
- Status: confirmed by real API call
- Backend files:
  - `backend/modules/tasks/router.py`
  - `backend/core/websocket.py`
- What happens:
  - The task creation flow writes the task and then tries to publish a WebSocket event.
  - The event payload includes raw `UUID` objects in `payload.tasks`.
  - Redis/WebSocket publish uses `json.dumps(...)`, which fails on Python `UUID`.
- Observed backend error:
  - `TypeError: Object of type UUID is not JSON serializable`
- User-facing impact:
  - Frontend "Add task" will appear to fail.
  - The task may already be persisted even though the API response is `500`.
  - Frontend state and backend state can become inconsistent after submission.

### 2. Local Vite frontend is blocked by backend CORS policy
- Status: confirmed by preflight requests
- Backend file:
  - `backend/config.py`
- Frontend file:
  - `frontend/vite.config.ts`
- What happens:
  - Backend allows `http://localhost:3000`
  - Frontend dev server runs on `http://localhost:5173`
- Verified behavior:
  - `Origin: http://localhost:3000` -> allowed
  - `Origin: http://localhost:5173` -> `Disallowed CORS origin`
- User-facing impact:
  - Running `npm run dev` for the frontend will fail to call backend APIs in the browser unless CORS is adjusted.

### 3. Frontend sample env points to `localhost:8000`, which was not stable in this environment
- Status: observed in this machine during check
- Frontend file:
  - `frontend/.env.example`
- What happens:
  - Sample config uses:
    - `VITE_API_BASE_URL=http://localhost:8000`
    - `VITE_WS_BASE_URL=ws://localhost:8000`
  - During this check, backend became reachable on `127.0.0.1:8000`, while `localhost:8000` was not reliable.
- User-facing impact:
  - On this machine, frontend may fail to connect if using the sample env values unchanged.
- Note:
  - This is environment-specific risk, not a confirmed application logic bug.

## Verified Working Read Paths
- `GET /health`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/dashboard`
- `GET /api/briefing/today`
- `GET /api/tasks`
- `GET /api/projects`
- `GET /api/files`
- `GET /api/tools/registry`
- `GET /api/settings/llm`
- `GET /api/settings/email`
- `GET /api/settings/users`
- WebSocket authenticated connection to `/ws` could be established

## Not Checked in This Pass
- File upload flow
- Risk Analyzer execution flow
- Full browser rendering through a running frontend dev server

## Notes
- One temporary integration-check task was created during testing and then deleted.
- The problems above are recorded from actual runtime behavior, not just static inspection.
