# Архитектура проекта

## Общая идея

Персональная платформа на VPS для:
1. **Хостинга сайтов/приложений** — любой сайт разворачивается как Docker-контейнер за общим reverse proxy
2. **Task Manager** — система управления задачами с веб-интерфейсом, REST API и интеграцией с Claude AI через MCP

## Инфраструктура

```
┌─────────────────────────────────────────────────────┐
│                        VPS                          │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │              Traefik (reverse proxy)           │  │
│  │         :80 (HTTP) → :443 (HTTPS)             │  │
│  │         Let's Encrypt auto-certificates       │  │
│  └──────────┬────────────────────┬───────────────┘  │
│             │                    │                   │
│    cdn.sheshenin.com    tasks.sheshenin.com          │
│             │                    │                   │
│  ┌──────────▼──────┐  ┌─────────▼──────────────┐   │
│  │   marsvpn-app   │  │     tasks-api          │   │
│  │   nginx:alpine  │  │   python:3.12-slim     │   │
│  │   (статика)     │  │   FastAPI + uvicorn    │   │
│  │   порт 80       │  │   порт 8000            │   │
│  └─────────────────┘  │                        │   │
│                       │  SQLite (volume)       │   │
│                       │  iCal calendar sync    │   │
│                       │  MCP Streamable HTTP   │   │
│                       └────────────────────────┘   │
│                                                     │
│  Docker network: proxy_default (общая для Traefik)  │
└─────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Traefik (внешний)
- Живёт в отдельном docker-compose (`/home/deploy/traefik/` или аналог)
- Слушает порты 80/443
- Автоматически выпускает Let's Encrypt сертификаты
- Маршрутизирует запросы по доменам через Docker labels
- Общая сеть `proxy_default` — все сервисы подключаются к ней

### 2. marsvpn-app (landing page)
- **Домен:** `cdn.sheshenin.com`
- **Технология:** nginx:alpine, статический HTML
- **Файлы:** `Dockerfile` → копирует `index.html`
- Просто лендинг "sheshenin.com — Hosting platform — Online"

### 3. tasks-api (Task Manager)
- **Домен:** `tasks.sheshenin.com`
- **Технология:** Python 3.12, FastAPI, uvicorn, SQLite
- **Аутентификация:** Bearer token (env `TASKS_API_TOKEN`)
- **Данные:** SQLite в Docker volume `tasks-data`
- **Бэкапы:** автоматические при каждой мутации, хранятся 10 дней

## Docker Compose

```yaml
services:
  app:           # nginx landing → cdn.sheshenin.com
  tasks-api:     # FastAPI task manager → tasks.sheshenin.com

volumes:
  tasks-data:    # SQLite + backups

networks:
  proxy_default: # Traefik shared network (external)
```

## Добавление нового сервиса

Для нового сайта/приложения:
1. Создать `Dockerfile` для нового сервиса
2. Добавить сервис в `docker-compose.yml`
3. Указать Traefik labels с нужным доменом
4. Подключить к сети `proxy_default`
5. `docker compose up -d --build <service>`
