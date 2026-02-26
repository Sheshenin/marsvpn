# Статус проекта

**Дата:** 2026-02-26

## Что работает

### Landing page (`cdn.sheshenin.com`)
- [x] nginx + статический HTML
- [x] HTTPS через Traefik + Let's Encrypt
- [x] Деплой через GitHub Actions

### Task Manager (`tasks.sheshenin.com`)
- [x] SQLite база данных (projects, tasks, calendars)
- [x] REST API (CRUD для tasks, projects, calendars)
- [x] Веб-интерфейс (SPA, vanilla JS, тёмная тема)
- [x] MCP Streamable HTTP endpoint (`POST /mcp`, `GET /mcp` SSE)
- [x] MCP stdio server для Claude Code CLI
- [x] iCal календарь — синхронизация событий
- [x] Daily overview endpoint
- [x] In-memory кэш с инвалидацией при мутациях
- [x] Автоматические бэкапы SQLite
- [x] Bearer token аутентификация для REST API
- [x] Docker volume для персистентных данных
- [x] OAuth 2.1 + PKCE endpoints (для MCP remote auth)
- [x] `GET /mcp` SSE keepalive endpoint
- [x] `/.well-known/oauth-protected-resource` endpoint
- [x] `/.well-known/oauth-authorization-server` endpoint
- [x] `POST /register` — Dynamic Client Registration (RFC 7591)
- [x] `GET /authorize` — auto-approve, PKCE redirect
- [x] `POST /token` — PKCE validation, выдаёт API токен
- [x] Фавикон (emoji ✅, inline SVG)
- [x] Задачи остаются видны после пометки done до перезагрузки страницы
- [x] Undo: повторный клик на done возвращает предыдущий статус

### CI/CD
- [x] GitHub Actions — автодеплой при push (**сейчас отключён**, см. ниже)
- [x] SSH деплой на VPS
- [x] Docker Compose оркестрация

## Текущая проблема (2026-02-21)

### MCP подключение из claude.ai не работает после подключения Cloudflare

**Симптом:** "McpAuthorizationError: Your account was authorized but the integration rejected the credentials"

**Что происходит по логам:**
1. `POST /mcp` → 200 OK (initialize успешен)
2. `GET /.well-known/oauth-protected-resource/mcp` → 200
3. `GET /.well-known/oauth-authorization-server` → 200
4. `POST /register` → 201 (client registered)
5. `GET /authorize` → 302 (redirect to `https://claude.ai/api/mcp/auth_callback`)
6. `GET /.well-known/oauth-authorization-server` → 200 (повторно, от claude.ai server)
7. `POST /token` → 200 (токен выдан успешно)
8. **После этого — ничего.** Claude.ai не делает финальный `POST /mcp` с токеном.

**Что было проверено:**
- Authorization header проходит через Cloudflare ✓
- `/mcp` открытый (без auth) — та же картина ✓
- resource URL с trailing slash (`https://tasks.sheshenin.com/`) — совпадает ✓
- `resource` поле добавлено в ответ `/token` ✓
- протокол обновлён до `2025-03-26` ✓
- `Mcp-Session-Id` header добавлен ✓
- `GET /mcp` SSE endpoint добавлен ✓

**Гипотезы:**
- Claude.ai клиент отвергает токен client-side без видимой причины
- Возможна проблема с Cloudflare (раньше работало без Cloudflare)
- Возможно claude.ai требует JWT вместо opaque token
- Возможно нужен refresh_token в ответе `/token`

**Текущее состояние кода:**
- `/mcp` — открытый (без auth проверки), для диагностики
- Добавлено детальное логирование всех запросов с телами
- OAuth endpoints полностью реализованы

## Известные ограничения

- MCP подключение из claude.ai сломано (см. выше)
- Деплой удаляет папку и делает fresh clone — `.env` теряется при деплое
- `git clone` падает если в директории остались docker-owned файлы (owned by root)
- Календарь подгружается синхронно (может тормозить при медленных iCal-серверах)

## CI/CD (GitHub Actions)

**Статус: отключён** (2026-02-26)

Workflow "Deploy to VPS" отключён вручную из-за проблемы с деплоем:
деплой-скрипт не может удалить docker-owned файлы → `git clone` падает в непустую папку → сервер остаётся в сломанном состоянии.

```bash
# Включить обратно:
gh workflow enable "Deploy to VPS" -R Sheshenin/marsvpn

# Отключить:
gh workflow disable "Deploy to VPS" -R Sheshenin/marsvpn

# Проверить статус:
gh workflow list -R Sheshenin/marsvpn
```

**Ручной деплой (пока Actions отключён):**
```bash
cd /home/deploy/app/marsvpn
docker compose up -d --build
```

## Changelog

### 2026-02-26
- Добавлен фавикон ✅ (emoji через inline SVG data URL)
- Веб-интерфейс: задачи остаются видимы после нажатия done до перезагрузки (`doneThisSession`)
- Undo done: повторный клик возвращает предыдущий статус задачи
- Inbox-задачи исключены из раздела "All Tasks"
- GitHub Actions "Deploy to VPS" отключён (проблема с docker-owned файлами при деплое)

### 2026-02-21
- Добавлен OAuth 2.1 + PKCE (register, authorize, token endpoints)
- Обновлён protocolVersion до `2025-03-26`
- Добавлен `GET /mcp` SSE keepalive endpoint
- Добавлен `Mcp-Session-Id` header в initialize response
- Добавлено `resource` поле в `/token` response (RFC 8707)
- Исправлен resource URL — trailing slash для соответствия claude.ai
- Исправлен case-insensitive Bearer token check
- Добавлена зависимость `python-multipart` для Form data
- Добавлено детальное логирование запросов (диагностика)
- **Статус: MCP подключение не работает, диагностика продолжается**

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
