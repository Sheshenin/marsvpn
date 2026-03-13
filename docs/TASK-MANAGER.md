# Task Manager — детальная документация

## Назначение

Персональная система управления задачами с тремя точками доступа:
- **Веб-интерфейс** — `https://tasks.sheshenin.com/`
- **REST API** — `https://tasks.sheshenin.com/tasks`, `/inbox`, `/projects`, ...
- **MCP (Model Context Protocol)** — `https://tasks.sheshenin.com/mcp` для Claude AI

## Модель данных

### SQLite схема (`tasks/schema.sql`)

```
projects
├── id (PK, autoincrement)
├── name (unique)
├── description
└── created_at

tasks
├── id (PK, autoincrement)
├── title
├── details
├── project_id (FK → projects)
├── status: inbox | active | waiting | done | cancelled
├── deadline (YYYY-MM-DD)
├── created_at
└── updated_at

calendars
├── id (PK, autoincrement)
├── name
├── url (iCal .ics URL)
└── created_at
```

### Жизненный цикл задачи

```
  быстрый ввод        разобрать         работа
  ───────────► inbox ──────────► active ──────────► done
                                   │
                                   ├──► waiting (ждём кого-то)
                                   │       │
                                   │       └──► active (снова)
                                   │
                                   └──► cancelled
```

## Структура кода

```
tasks/
├── __init__.py          # пустой, делает tasks пакетом
├── Dockerfile           # python:3.12-slim + pip install + copy tasks/
├── requirements.txt     # fastapi, uvicorn, icalendar, httpx
├── schema.sql           # DDL для SQLite
├── db.py                # CRUD операции с SQLite
├── api.py               # FastAPI app — REST API + Web UI + MCP endpoint
├── mcp_server.py        # MCP tools definitions + stdio handler + call_tool()
├── calendar.py          # iCal fetch + parse (httpx + icalendar)
├── SETUP.md             # инструкция по установке и подключению
├── .gitignore           # *.db, __pycache__/
└── static/
    └── index.html       # SPA веб-интерфейс (vanilla JS)
```

### db.py — Database layer
- `init_db()` — CREATE IF NOT EXISTS при импорте
- `backup_db()` — SQLite online backup после каждой мутации
- CRUD: `add_task`, `get_task`, `list_tasks`, `update_task`, `complete_task`, `delete_task`
- Projects: `create_project`, `list_projects`, `delete_project`
- Calendars: `add_calendar`, `list_calendars`, `delete_calendar`
- Queries: `overdue_tasks`, `tasks_due_today`, `task_summary`
- DB path: env `TASKS_DB_PATH` (default: `tasks/tasks.db`)

### api.py — FastAPI application
- **Middleware:** после каждого POST/PATCH/DELETE инвалидирует кэш и делает backup
- **Кэш:** in-memory dict, перестраивается при первом GET после мутации
- **GET `/`** — отдаёт `static/index.html` с подставленным API_TOKEN
- **GET `/api/cache`** — единый JSON для фронтенда (tasks, projects, overdue, due_today, calendar_events)
- **REST endpoints:** /tasks, /inbox, /projects, /calendars, /overview
- **POST `/mcp`** — MCP Streamable HTTP endpoint (без auth, публичный)

### mcp_server.py — MCP интеграция
- `TOOLS` — список 15 MCP tools (inbox, tasks, projects, calendars, overview)
- `call_tool(name, args)` — диспетчер вызовов
- `main()` — stdio MCP server (для Claude Code CLI)
- Используется двумя путями:
  - **Claude AI (claude.ai)** → POST `/mcp` (Streamable HTTP, обрабатывается в api.py)
  - **Claude Code (CLI)** → `python -m tasks.mcp_server` (stdio)

### calendar.py — iCal интеграция
- Скачивает .ics файлы через httpx
- Парсит с помощью icalendar
- `get_events(url, days_back, days_forward)` — события в диапазоне
- `get_today_tomorrow_events(url)` — сегодня + завтра

### static/index.html — Веб-интерфейс (SPA)
- Vanilla JS, никаких фреймворков
- Тёмная тема (GitHub-like)
- Секции: быстрый ввод, календарь (3 дня), `Все активные`, `Ждём / Сделано`, Inbox
- Верхний блок `Все активные`: только `active`, группировка по проектам, сортировка по deadline
- Нижний блок `Ждём / Сделано`: два фильтра `waiting` и `done/cancelled`, без active-задач
- Модальное окно редактирования задачи
- Оптимистичный UI при toggle done

## REST API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | / | - | Веб-интерфейс |
| GET | /api/cache | Bearer | Единый кэш для фронтенда |
| POST | /inbox | Bearer | Быстрое добавление в inbox |
| GET | /inbox | Bearer | Список inbox |
| GET | /tasks | Bearer | Список задач (?status, ?project_id, ?include_done) |
| POST | /tasks | Bearer | Создать задачу |
| GET | /tasks/{id} | Bearer | Одна задача |
| PATCH | /tasks/{id} | Bearer | Обновить поля задачи |
| POST | /tasks/{id}/complete | Bearer | Завершить задачу |
| DELETE | /tasks/{id} | Bearer | Удалить задачу |
| GET | /projects | Bearer | Список проектов |
| POST | /projects | Bearer | Создать проект |
| DELETE | /projects/{id} | Bearer | Удалить проект |
| GET | /calendars | Bearer | Список календарей |
| POST | /calendars | Bearer | Добавить iCal календарь |
| DELETE | /calendars/{id} | Bearer | Удалить календарь |
| GET | /calendar/events | Bearer | События (?days_back, ?days_forward) |
| GET | /overview | Bearer | Daily overview (всё сразу) |
| POST | /mcp | - | MCP Streamable HTTP endpoint |

## Аутентификация

- Bearer token в env `TASKS_API_TOKEN`
- Если токен не задан — API открыт (dev mode)
- MCP endpoint `/mcp` — без аутентификации (публичный)
- Токен подставляется в веб-интерфейс при рендере HTML

## План переноса фронтенда (аналогично shopping-list)

Цель: вынести UI Task Manager на Vercel, оставить API/MCP и БД на сервере.

1. Зафиксировать целевую архитектуру:
- Frontend: Vercel (`*.vercel.app`) на этапе миграции.
- Backend/API/MCP/SQLite: остаются в `tasks-api` на сервере.
- Старый UI на `tasks.sheshenin.com` временно оставить как rollback.

2. Исправить auth-модель перед выносом фронта:
- Убрать зависимость от инъекции `__API_TOKEN__` в HTML.
- Добавить пользовательский login-flow (session/JWT/cookie) для внешнего frontend.
- `TASKS_API_TOKEN` оставить для server-to-server и админских вызовов.

3. Подготовить backend для внешнего UI:
- Ограничить CORS (вместо `*`) на production/preview origins.
- Добавить стабильный агрегированный endpoint для frontend (`/snapshot` или расширенный `/api/cache` контракт).
- Не менять контракт MCP `/mcp`.

4. Подготовить frontend-контур:
- Отдельный frontend-проект (желательно Next.js).
- `NEXT_PUBLIC_API_URL` + same-origin `/api` через `rewrites` на серверный API.
- Обработка 401/403/timeout с понятным UX (logout/retry/error state).

5. Миграция без простоя:
- Этап A: deploy на `*.vercel.app`, внутреннее тестирование.
- Этап B: dual-run (старый server UI + новый Vercel UI).
- Этап C: после стабилизации перенос домена (по необходимости).

6. Валидация перед переключением:
- Проверить сценарии: inbox add, CRUD задач, complete/undo, projects, calendars, overview.
- Добавить release marker и лёгкий API probe для диагностики кэша/версии.
- Подготовить rollback: возврат на server UI за один шаг.

7. Операционный порядок:
- Документация (`STATUS.md`, `TASK-MANAGER.md`) обновляется до переключения трафика.
- Деплой по текущему workflow: локально на сервере, затем git push.
