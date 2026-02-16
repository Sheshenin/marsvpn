# Статус проекта

**Дата:** 2026-02-17

## Что работает

### Landing page (`cdn.sheshenin.com`)
- [x] nginx + статический HTML
- [x] HTTPS через Traefik + Let's Encrypt
- [x] Деплой через GitHub Actions

### Task Manager (`tasks.sheshenin.com`)
- [x] SQLite база данных (projects, tasks, calendars)
- [x] REST API (CRUD для tasks, projects, calendars)
- [x] Веб-интерфейс (SPA, vanilla JS, тёмная тема)
- [x] MCP Streamable HTTP endpoint для Claude AI
- [x] MCP stdio server для Claude Code
- [x] iCal календарь — синхронизация событий
- [x] Daily overview endpoint
- [x] In-memory кэш с инвалидацией при мутациях
- [x] Автоматические бэкапы SQLite (при каждой мутации, хранятся 10 дней)
- [x] Bearer token аутентификация
- [x] Docker volume для персистентных данных

### CI/CD
- [x] GitHub Actions — автодеплой при push
- [x] SSH деплой на VPS
- [x] Docker Compose оркестрация

## Известные ограничения

- Деплой удаляет папку и делает fresh clone — .env теряется при деплое
- MCP endpoint `/mcp` не требует аутентификации
- Календарь подгружается синхронно (может тормозить при медленных iCal-серверах)
- Веб-интерфейс — mobile-friendly, но без PWA/offline

## Changelog

### 2026-02-17
- fix: кнопка "done" в веб-интерфейсе — добавлен оптимистичный UI и обработка ошибок
- Увеличен размер чекбокса (20px → 24px) для лучшей кликабельности
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
