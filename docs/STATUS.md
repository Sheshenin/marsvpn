# Статус проекта

**Дата:** 2026-03-14

## Что работает

### Landing page (`cdn.sheshenin.com`)
- [x] nginx + статический HTML
- [x] HTTPS через Traefik + Let's Encrypt

### Task Manager (`tasks.sheshenin.com`)
- [x] SQLite база данных (projects, tasks, calendars)
- [x] REST API (CRUD для tasks, projects, calendars)
- [x] Веб-интерфейс (SPA, vanilla JS, тёмная тема)
- [x] MCP Streamable HTTP endpoint (`POST /mcp`, без auth — для openclaw на том же сервере)
- [x] MCP stdio server для Claude Code CLI
- [x] iCal календарь — 2 календаря iCloud подключены
- [x] Daily overview endpoint
- [x] In-memory кэш с инвалидацией при мутациях
- [x] Автоматические бэкапы SQLite
- [x] Bearer token аутентификация для REST API
- [x] Docker volume для персистентных данных
- [x] Фавикон (emoji ✅, inline SVG)
- [x] Задачи остаются видны после пометки done до перезагрузки страницы
- [x] Undo: повторный клик на done возвращает предыдущий статус

### CI/CD
- [x] GitHub Actions (**отключён**, см. ниже)
- [x] Docker Compose оркестрация

## Текущий workflow (рабочий)

Работаем напрямую на сервере, CI/CD не используем:

1. Правим код в `/home/deploy/app/marsvpn`
2. `docker compose up -d --build` — деплоим локально
3. Пушим в git — только для version control

```bash
# Деплой
cd /home/deploy/app/marsvpn
docker compose up -d --build

# Пуш в git (из той же папки — там есть .git)
git add -p
git commit -m "..."
git push origin claude/task-database-schema-uYF63
```

## CI/CD (GitHub Actions)

**Статус: отключён** (2026-02-26)

Причина: deploy-скрипт делает `git clone` в директорию с docker-owned файлами → клонирование падает → сервер ломается. Дополнительно: `docker compose down` без `--volumes` теперь, но риск потери `.env` при свежем clone остаётся.

```bash
gh workflow enable "Deploy to VPS" -R Sheshenin/marsvpn   # включить
gh workflow disable "Deploy to VPS" -R Sheshenin/marsvpn  # отключить
gh workflow list -R Sheshenin/marsvpn                      # статус
```

## Известные ограничения

- OAuth 2.1 + PKCE код был написан (2026-02-21) но **не закоммичен** → потерян при сбое деплоя
- MCP подключение из claude.ai не работает (OAuth не реализован в текущем коде)
- `.env` теряется при fresh clone — нужно восстанавливать вручную
- Календарь подгружается синхронно (может тормозить при медленных iCal-серверах)
- Данные (задачи) хранятся только в docker volume — при `docker compose down --volumes` теряются

## Конфигурация

### .env
```
TASKS_API_TOKEN=<токен>
TASKS_BASE_URL=https://tasks.sheshenin.com
```
> При пересоздании контейнера `.env` нужно восстанавливать вручную.

### Календари (в БД)
- iCloud (личный) — `p66-caldav.icloud.com`
- iCloud 2 (семейный/учёба) — `p101-caldav.icloud.com`

> URL-ы хранятся в таблице `calendars` в SQLite. `webcal://` → `https://`.

### Openclaw → MCP
- mcporter: `https://tasks.sheshenin.com/mcp` (без auth, открытый)
- 16 инструментов: inbox, tasks, projects, calendars, daily_overview

## Changelog

### 2026-03-14
- Веб-интерфейс Task Manager перестроен:
  - верхний блок `Today & Tomorrow` заменён на `Все активные`;
  - активные задачи теперь группируются по проектам и сортируются по датам;
  - нижний блок оставлен только для двух режимов: `Ждём` (`waiting`) и `Сделано` (`done/cancelled`);
  - активные задачи из нижнего списка убраны.
- Добавлено inline-редактирование прямо в списках задач:
  - клик по сроку открывает date picker и сразу сохраняет новый deadline;
  - клик по status badge переключает `active ↔ waiting`, а для `inbox` открывает выбор статуса;
  - клик по project tag открывает выбор проекта и сразу переносит задачу;
  - те же controls доступны и в `Inbox` для project/status/deadline.
- Поведение completed-списка и undo уточнено:
  - в `Сделано` задачи сортируются по `updated_at` в обратном порядке;
  - после отметки done задача остаётся на прежнем месте 15 секунд для быстрого отката.

### 2026-03-09
- Добавлен детальный план переноса frontend Task Manager (Vercel + server API) в `docs/TASK-MANAGER.md`.
- Зафиксирован ключевой риск: текущая модель `__API_TOKEN__` в HTML не подходит для отделённого публичного frontend и требует отдельного login/session слоя.

### 2026-02-27
- Восстановлены данные после сбоя: 35 задач из GTD-выгрузки (18 active, 17 waiting)
- Подключены 2 календаря iCloud
- Установлен рабочий workflow: правим на сервере → docker compose → git push
- `/home/deploy/app/marsvpn` теперь полноценный git-репозиторий (не только deployed copy)

### 2026-03-06
- В веб-интерфейсе список "All Tasks" получил третий фильтр `Completed` (done/cancelled) и стал взаимно исключающим с `Active` и `All`

### 2026-02-26
- **Инцидент:** CI/CD сломал деплой → потеря незакоммиченного кода (OAuth) и данных БД
- Добавлен фавикон ✅ (emoji через inline SVG data URL)
- Веб-интерфейс: задачи остаются видимы после нажатия done до перезагрузки (`doneThisSession`)
- Undo done: повторный клик возвращает предыдущий статус задачи
- Inbox-задачи исключены из раздела "All Tasks"
- GitHub Actions "Deploy to VPS" отключён
- `docker compose down --volumes` → `docker compose down` (данные больше не сносятся при деплое)

### 2026-02-21
- Написан OAuth 2.1 + PKCE (register, authorize, token endpoints) — **не закоммичен, потерян**
- Обновлён protocolVersion до `2025-03-26` — **не закоммичен, потерян**
- Добавлен `GET /mcp` SSE keepalive endpoint — **не закоммичен, потерян**
- **Статус: MCP подключение из claude.ai не работает**

### 2026-02-17
- fix: кнопка "done" в веб-интерфейсе — оптимистичный UI
- Увеличен размер чекбокса (20px → 24px)
- Создана документация проекта (`docs/`)

### 2026-02-16
- feat: Task Manager — полный REST API + веб-интерфейс
- feat: MCP Streamable HTTP endpoint для Claude AI
- feat: iCal календарь интеграция
- feat: GitHub Actions CI/CD

### Ранее
- Настройка Traefik + Let's Encrypt
- Landing page на `cdn.sheshenin.com`
- Удалена старая конфигурация shadowsocks
