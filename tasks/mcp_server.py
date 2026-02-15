"""MCP (Model Context Protocol) server for task management.

This exposes task operations as MCP tools that Claude AI can call.
Run with: python -m tasks.mcp_server
"""

import json
import sys
from datetime import datetime

from tasks import db


def send_response(response: dict):
    """Write a JSON-RPC response to stdout."""
    data = json.dumps(response)
    header = f"Content-Length: {len(data)}\r\n\r\n"
    sys.stdout.write(header + data)
    sys.stdout.flush()


def handle_initialize(req_id, params):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "task-manager",
                "version": "1.0.0",
            },
        },
    }


TOOLS = [
    {
        "name": "inbox_add",
        "description": "Quick-add text to inbox without categorization. Use for capturing raw thoughts, forwarded messages, or anything that needs processing later.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Raw text to add to inbox"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "list_inbox",
        "description": "Show all items in inbox that need to be processed and categorized.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_task",
        "description": "Add a structured task with title, details, project, status, and deadline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "details": {"type": "string", "description": "Additional details"},
                "project_id": {"type": "integer", "description": "Project ID to assign to"},
                "status": {
                    "type": "string",
                    "enum": ["active", "waiting"],
                    "description": "Task status (default: active)",
                },
                "deadline": {"type": "string", "description": "Deadline in YYYY-MM-DD format"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks filtered by status and/or project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["inbox", "active", "waiting", "done", "cancelled"],
                    "description": "Filter by status",
                },
                "project_id": {"type": "integer", "description": "Filter by project"},
                "include_done": {"type": "boolean", "description": "Include completed tasks"},
            },
        },
    },
    {
        "name": "get_task",
        "description": "Get details of a specific task by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "update_task",
        "description": "Update task fields (title, details, project_id, status, deadline).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID to update"},
                "title": {"type": "string"},
                "details": {"type": "string"},
                "project_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["inbox", "active", "waiting", "done", "cancelled"]},
                "deadline": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as done.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID to complete"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "delete_task",
        "description": "Delete a task permanently.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID to delete"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "list_projects",
        "description": "List all projects.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_project",
        "description": "Create a new project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "description": {"type": "string", "description": "Project description"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "daily_overview",
        "description": "Get a full daily overview: summary, overdue tasks, due today, inbox, active and waiting tasks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle_tools_list(req_id, params):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": TOOLS},
    }


def call_tool(name: str, args: dict) -> str:
    """Execute a tool and return result as text."""
    if name == "inbox_add":
        tid = db.inbox_add(args["text"])
        return f"Added to inbox as task #{tid}"

    elif name == "list_inbox":
        items = db.list_inbox()
        if not items:
            return "Inbox is empty."
        lines = [f"[{t['id']}] {t['title']}" for t in items]
        return "Inbox:\n" + "\n".join(lines)

    elif name == "add_task":
        tid = db.add_task(
            title=args["title"],
            details=args.get("details"),
            project_id=args.get("project_id"),
            status=args.get("status", "active"),
            deadline=args.get("deadline"),
        )
        return f"Created task #{tid}: {args['title']}"

    elif name == "list_tasks":
        tasks = db.list_tasks(
            status=args.get("status"),
            project_id=args.get("project_id"),
            include_done=args.get("include_done", False),
        )
        if not tasks:
            return "No tasks found."
        lines = []
        for t in tasks:
            dl = t["deadline"] or "no deadline"
            proj = t["project_name"] or "-"
            lines.append(f"[{t['id']}] [{t['status']}] {t['title']} | project: {proj} | deadline: {dl}")
        return "\n".join(lines)

    elif name == "get_task":
        t = db.get_task(args["task_id"])
        if not t:
            return f"Task #{args['task_id']} not found."
        return json.dumps(t, indent=2, default=str)

    elif name == "update_task":
        tid = args.pop("task_id")
        ok = db.update_task(tid, **args)
        return f"Task #{tid} updated." if ok else f"Task #{tid} not found."

    elif name == "complete_task":
        ok = db.complete_task(args["task_id"])
        return f"Task #{args['task_id']} completed." if ok else f"Task #{args['task_id']} not found."

    elif name == "delete_task":
        db.delete_task(args["task_id"])
        return f"Task #{args['task_id']} deleted."

    elif name == "list_projects":
        projects = db.list_projects()
        if not projects:
            return "No projects."
        lines = [f"[{p['id']}] {p['name']}: {p['description'] or ''}" for p in projects]
        return "\n".join(lines)

    elif name == "create_project":
        pid = db.create_project(args["name"], args.get("description"))
        return f"Created project #{pid}: {args['name']}"

    elif name == "daily_overview":
        overview = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": db.task_summary(),
            "overdue": db.overdue_tasks(),
            "due_today": db.tasks_due_today(),
            "inbox": db.list_inbox(),
            "active": db.list_tasks(status="active"),
            "waiting": db.list_tasks(status="waiting"),
        }
        return json.dumps(overview, indent=2, default=str)

    return f"Unknown tool: {name}"


def handle_tools_call(req_id, params):
    name = params.get("name", "")
    args = params.get("arguments", {})
    try:
        result_text = call_tool(name, args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result_text}],
            },
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            },
        }


HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def main():
    """Run MCP server over stdio."""
    buf = ""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        buf += line

        # Parse Content-Length header
        if "Content-Length:" in buf:
            try:
                header_end = buf.index("\r\n\r\n")
            except ValueError:
                continue

            header_part = buf[:header_end]
            length = int(header_part.split("Content-Length:")[1].strip())
            body_start = header_end + 4
            body = buf[body_start:body_start + length]

            if len(body) < length:
                continue  # wait for more data

            buf = buf[body_start + length:]

            request = json.loads(body)
            method = request.get("method", "")
            req_id = request.get("id")

            # Notifications (no id) — just acknowledge
            if req_id is None:
                continue

            handler = HANDLERS.get(method)
            if handler:
                response = handler(req_id, request.get("params", {}))
                send_response(response)
            else:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                })


if __name__ == "__main__":
    main()
