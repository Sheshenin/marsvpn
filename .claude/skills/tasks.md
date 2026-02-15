# Skill: Task Management (/tasks)

Manage personal task list stored in a local SQLite database.

## Database location

`tasks/tasks.db` (auto-created on first use via `tasks/db.py`).

## How to use

Run operations via Python using the `tasks/db.py` module. Always run from the project root.

### Initialize (if needed)

```bash
cd /home/user/marsvpn && python -c "from tasks.db import init_db; init_db()"
```

### List active tasks

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import list_tasks
for t in list_tasks():
    deadline = t['deadline'] or 'no deadline'
    project = t['project_name'] or 'no project'
    print(f\"[{t['id']}] [{t['status']}] {t['title']} | project: {project} | deadline: {deadline}\")
"
```

### Add a new task

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import add_task
tid = add_task(
    title='Task title here',
    details='Optional details',
    project_id=None,        # or project ID number
    status='active',        # 'active' or 'waiting'
    deadline='2026-03-01',  # YYYY-MM-DD or None
)
print(f'Created task #{tid}')
"
```

### Update a task

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import update_task
update_task(TASK_ID, title='New title', status='waiting', deadline='2026-04-01')
"
```

### Complete a task

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import complete_task
complete_task(TASK_ID)
"
```

### Delete a task

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import delete_task
delete_task(TASK_ID)
"
```

### Projects — create and list

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import create_project
pid = create_project('Project Name', 'Optional description')
print(f'Created project #{pid}')
"
```

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import list_projects
for p in list_projects():
    print(f\"[{p['id']}] {p['name']}: {p['description'] or ''}\")
"
```

### Overdue tasks

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import overdue_tasks
for t in overdue_tasks():
    print(f\"[{t['id']}] {t['title']} — deadline was {t['deadline']}\")
"
```

### Task summary (counts by status)

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import task_summary
for status, count in task_summary().items():
    print(f'{status}: {count}')
"
```

## Statuses

- `active` — task is in progress or ready to work on
- `waiting` — task is blocked or deferred
- `done` — completed
- `cancelled` — no longer needed

## Deadline format

Always use `YYYY-MM-DD` for deadlines.
