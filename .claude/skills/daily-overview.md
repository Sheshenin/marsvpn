# Skill: Daily Overview (/daily-overview)

Generate a morning briefing: check tasks, email, and calendar, then present a structured overview of the day.

## Steps to perform

### 1. Check task list

Run the following to get today's tasks, overdue items, and summary:

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import list_tasks, tasks_due_today, overdue_tasks, task_summary
from datetime import datetime

print('=== TASK SUMMARY ===')
summary = task_summary()
for status, count in summary.items():
    print(f'  {status}: {count}')

print()
print('=== OVERDUE ===')
for t in overdue_tasks():
    print(f'  [{t[\"id\"]}] {t[\"title\"]} — deadline: {t[\"deadline\"]}')

print()
print('=== DUE TODAY ===')
for t in tasks_due_today():
    print(f'  [{t[\"id\"]}] {t[\"title\"]}')

print()
print('=== ALL ACTIVE TASKS ===')
for t in list_tasks(status='active'):
    deadline = t['deadline'] or 'no deadline'
    project = t['project_name'] or '-'
    print(f'  [{t[\"id\"]}] {t[\"title\"]} | project: {project} | deadline: {deadline}')

print()
print('=== WAITING TASKS ===')
for t in list_tasks(status='waiting'):
    deadline = t['deadline'] or 'no deadline'
    print(f'  [{t[\"id\"]}] {t[\"title\"]} | deadline: {deadline}')
"
```

### 2. Check email (if available)

If the user has configured email access (e.g. via MCP server, API, or CLI tool), check recent unread emails and summarize the important ones.

Common approaches:
- If an MCP email tool is available, use it
- If `gmail-cli` or similar is installed, run it
- If the user has a custom script, run it

If no email access is configured, note this and suggest the user set up email integration.

### 3. Check calendar (if available)

If the user has configured calendar access, check today's events.

Common approaches:
- If an MCP calendar tool is available, use it
- If `gcalcli` is installed: `gcalcli agenda --nocolor $(date +%Y-%m-%d) $(date -d '+1 day' +%Y-%m-%d)`
- If the user has a custom script, run it

If no calendar access is configured, note this and suggest the user set up calendar integration.

### 4. Present the daily overview

Format the output as a structured briefing:

```
## Daily Overview — [today's date]

### Tasks
- **Overdue:** [count] tasks need attention
- **Due today:** [list]
- **Active:** [count] tasks in progress
- **Waiting:** [count] tasks on hold

### Email highlights
- [Summary of important emails, or note that email is not configured]

### Calendar
- [Today's events, or note that calendar is not configured]

### Suggested focus
- [Top 2-3 items to prioritize based on deadlines and importance]
```

## Setting up as a recurring task

To get this overview automatically, add a recurring task:

```bash
cd /home/user/marsvpn && python -c "
from tasks.db import add_task
add_task(
    title='Morning briefing: run /daily-overview',
    details='Run daily overview skill to check tasks, email, and calendar',
    status='active',
    deadline=None,  # recurring, no specific deadline
)
"
```

Then start each Claude Code session with `/daily-overview` to get the briefing.

## Email & calendar integration notes

For full daily overview functionality, configure one of:
- **Google Workspace**: install `gcalcli` and configure Gmail API access
- **MCP servers**: add email/calendar MCP servers to `.claude/settings.json`
- **Custom scripts**: place scripts in `tasks/integrations/` that output JSON
