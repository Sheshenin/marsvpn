# Task Manager — Setup Guide

## 1. Deploy on server

```bash
# On the server where Traefik is running:
cd /path/to/marsvpn

# Create .env with your token
echo "TASKS_API_TOKEN=vKUr85iA6Yxj-4moWVduZpIooF5lwKrVjlr_FPpnt3w" > .env

# Deploy
docker compose up -d --build tasks-api
```

## 2. Verify it works

```bash
curl -H "Authorization: Bearer vKUr85iA6Yxj-4moWVduZpIooF5lwKrVjlr_FPpnt3w" \
  https://tasks.sheshenin.com/overview
```

## 3. Connect Claude AI (claude.ai)

Go to **Settings → MCP Servers → Add** in claude.ai and add:

- **Name**: Task Manager
- **URL**: `https://tasks.sheshenin.com/mcp`
- **Authentication**: Bearer token `vKUr85iA6Yxj-4moWVduZpIooF5lwKrVjlr_FPpnt3w`

After connecting, Claude will have these tools available:
- `inbox_add` — quick-add text to inbox
- `list_inbox` — show inbox items
- `add_task` — create a structured task
- `list_tasks` — list tasks by status/project
- `get_task` — get task details
- `update_task` — edit a task
- `complete_task` — mark as done
- `delete_task` — remove a task
- `list_projects` / `create_project` — manage projects
- `daily_overview` — full day briefing

## 4. Connect Claude Code (CLI)

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "task-manager": {
      "command": "python",
      "args": ["-m", "tasks.mcp_server"],
      "cwd": "/path/to/marsvpn"
    }
  }
}
```

## 5. Quick inbox from anywhere

### curl
```bash
curl -X POST https://tasks.sheshenin.com/inbox \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Разобрать письмо от клиента"}'
```

### Telegram bot (webhook handler)
Your bot forwards message text to:
```
POST https://tasks.sheshenin.com/inbox
{"text": "<message text>"}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /inbox | Quick add to inbox |
| GET | /inbox | List inbox items |
| GET | /tasks | List tasks (filters: status, project_id) |
| POST | /tasks | Create task |
| GET | /tasks/{id} | Get task |
| PATCH | /tasks/{id} | Update task |
| POST | /tasks/{id}/complete | Complete task |
| DELETE | /tasks/{id} | Delete task |
| GET | /projects | List projects |
| POST | /projects | Create project |
| DELETE | /projects/{id} | Delete project |
| GET | /overview | Daily overview |
| POST | /mcp | MCP endpoint for Claude AI |
