# CI/CD и workflow

## Схема работы

```
  Claude AI (claude.ai)          Claude Code (CLI на VPS)
  ─────────────────────          ────────────────────────
  Пишет код, коммитит,           Настраивает сервер:
  пушит в GitHub                 конфиги, docker-compose,
         │                       сети, отладка
         ▼
  GitHub Actions (deploy.yml)
         │
         ▼
  SSH → VPS: git clone + docker compose up -d --build
```

## GitHub Actions (`deploy.yml`)

**Триггер:** push в ветки `main` и `claude/task-database-schema-uYF63`

**Шаги:**
1. SSH на сервер через `appleboy/ssh-action`
2. `docker compose down --volumes` (останавливает старое)
3. Удаляет старую папку (включая docker-owned файлы через alpine контейнер)
4. `git clone -b $BRANCH` (свежий клон нужной ветки)
5. `docker compose up -d --build` (сборка и запуск)

**Секреты GitHub:**
- `SERVER_HOST` — IP/домен VPS
- `SERVER_USER` — SSH пользователь
- `SSH_PRIVATE_KEY` — приватный SSH ключ
- `GH_PAT` — GitHub Personal Access Token (для клонирования приватного репо)

## Ветки

- `main` — основная ветка
- `claude/setup-cicd-autodeploy-*` — рабочие ветки Claude AI
- `claude/task-database-schema-uYF63` — текущая ветка разработки Task Manager

## Важно

- Деплой полностью пересоздаёт папку (rm + clone), поэтому любые локальные изменения на сервере теряются
- Docker volumes (`tasks-data`) сохраняются между деплоями — данные SQLite не теряются
- `.env` файл пересоздаётся при деплое (нужно убедиться что он есть или использовать другой способ хранения секретов)
