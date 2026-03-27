"""Task management API server with MCP support."""

import json
import os
import uuid
from datetime import datetime
from functools import wraps

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from tasks import db
from tasks import calendar as cal
from tasks.mcp_server import TOOLS, call_tool

API_TOKEN = os.environ.get("TASKS_API_TOKEN", "")

# ── Cache ────────────────────────────────────────────────
_cache: dict | None = None


def build_cache() -> dict:
    """Build a single JSON with all data the frontend needs."""
    global _cache
    calendars = db.list_calendars()
    calendar_events = []
    for c in calendars:
        try:
            events = cal.get_events(c["url"], days_back=0, days_forward=3)
            for e in events:
                e["calendar"] = c["name"]
            calendar_events.extend(events)
        except Exception:
            pass
    calendar_events.sort(key=lambda e: e.get("start") or "")

    _cache = {
        "projects": db.list_projects(),
        "tasks": db.list_tasks(include_done=True),
        "overdue": db.overdue_tasks(),
        "due_today": db.tasks_due_today(),
        "calendar_events": calendar_events,
    }
    return _cache


def get_cache() -> dict:
    global _cache
    if _cache is None:
        return build_cache()
    return _cache


def invalidate_cache():
    global _cache
    _cache = None

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Task Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def backup_on_mutation(request: Request, call_next):
    response = await call_next(request)
    if request.method in ("POST", "PATCH", "DELETE") and response.status_code < 400:
        invalidate_cache()
        try:
            db.backup_db()
        except Exception:
            pass
    return response


# ── Web UI ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def web_ui():
    html = (STATIC_DIR / "index.html").read_text()
    return html.replace("__API_TOKEN__", API_TOKEN)


@app.get("/api/cache")
def api_cache(authorization: str = Header(None)):
    verify_token(authorization)
    return get_cache()


# ── Auth ──────────────────────────────────────────────────

def verify_token(authorization: str = Header(None)):
    if not API_TOKEN:
        return  # no token configured = open (dev mode)
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Models ────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    details: str | None = None
    project_id: int | None = None
    status: str = "active"
    deadline: str | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    details: str | None = None
    project_id: int | None = None
    status: str | None = None
    deadline: str | None = None

class InboxItem(BaseModel):
    text: str

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class CalendarCreate(BaseModel):
    name: str
    url: str


# ── Inbox (quick capture) ────────────────────────────────

@app.post("/inbox")
def inbox_add(item: InboxItem, authorization: str = Header(None)):
    verify_token(authorization)
    tid = db.inbox_add(item.text)
    return {"id": tid, "status": "inbox"}


@app.get("/inbox")
def inbox_list(authorization: str = Header(None)):
    verify_token(authorization)
    return db.list_inbox()


# ── Tasks ─────────────────────────────────────────────────

@app.get("/tasks")
def get_tasks(
    status: str | None = None,
    project_id: int | None = None,
    include_done: bool = False,
    authorization: str = Header(None),
):
    verify_token(authorization)
    return db.list_tasks(status=status, project_id=project_id, include_done=include_done)


@app.post("/tasks")
def create_task(task: TaskCreate, authorization: str = Header(None)):
    verify_token(authorization)
    tid = db.add_task(
        title=task.title,
        details=task.details,
        project_id=task.project_id,
        status=task.status,
        deadline=task.deadline,
    )
    return db.get_task(tid)


@app.get("/tasks/{task_id}")
def get_task(task_id: int, authorization: str = Header(None)):
    verify_token(authorization)
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, updates: TaskUpdate, authorization: str = Header(None)):
    verify_token(authorization)
    fields = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = db.update_task(task_id, **fields)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return db.get_task(task_id)


@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: int, authorization: str = Header(None)):
    verify_token(authorization)
    ok = db.complete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "status": "done"}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, authorization: str = Header(None)):
    verify_token(authorization)
    db.delete_task(task_id)
    return {"deleted": task_id}


# ── Projects ─────────────────────────────────────────────

@app.get("/projects")
def get_projects(authorization: str = Header(None)):
    verify_token(authorization)
    return db.list_projects()


@app.post("/projects")
def create_project(project: ProjectCreate, authorization: str = Header(None)):
    verify_token(authorization)
    pid = db.create_project(project.name, project.description)
    return db.get_project(pid)


@app.patch("/projects/{project_id}")
def update_project(project_id: int, updates: ProjectUpdate, authorization: str = Header(None)):
    verify_token(authorization)
    fields = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = db.update_project(project_id, **fields)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.get_project(project_id)


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, authorization: str = Header(None)):
    verify_token(authorization)
    result = db.delete_project(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": project_id, "moved_to_inbox": result["moved_tasks"]}


# ── Calendars ─────────────────────────────────────────────

@app.get("/calendars")
def get_calendars(authorization: str = Header(None)):
    verify_token(authorization)
    return db.list_calendars()


@app.post("/calendars")
def create_calendar(calendar: CalendarCreate, authorization: str = Header(None)):
    verify_token(authorization)
    cid = db.add_calendar(calendar.name, calendar.url)
    return {"id": cid, "name": calendar.name}


@app.delete("/calendars/{calendar_id}")
def remove_calendar(calendar_id: int, authorization: str = Header(None)):
    verify_token(authorization)
    db.delete_calendar(calendar_id)
    return {"deleted": calendar_id}


@app.get("/calendar/events")
def calendar_events(
    days_back: int = 7,
    days_forward: int = 7,
    authorization: str = Header(None),
):
    verify_token(authorization)
    calendars = db.list_calendars()
    all_events = []
    for c in calendars:
        try:
            events = cal.get_events(c["url"], days_back=days_back, days_forward=days_forward)
            for e in events:
                e["calendar"] = c["name"]
            all_events.extend(events)
        except Exception as exc:
            all_events.append({"calendar": c["name"], "error": str(exc)})
    all_events.sort(key=lambda e: e.get("start") or "")
    return all_events


# ── Overview ──────────────────────────────────────────────

@app.get("/overview")
def daily_overview(authorization: str = Header(None)):
    verify_token(authorization)
    calendars = db.list_calendars()
    calendar_events = []
    for c in calendars:
        try:
            events = cal.get_today_tomorrow_events(c["url"])
            for e in events:
                e["calendar"] = c["name"]
            calendar_events.extend(events)
        except Exception:
            pass
    calendar_events.sort(key=lambda e: e.get("start") or "")
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": db.task_summary(),
        "overdue": db.overdue_tasks(),
        "due_today": db.tasks_due_today(),
        "inbox": db.list_inbox(),
        "active": db.list_tasks(status="active"),
        "waiting": db.list_tasks(status="waiting"),
        "calendar_events": calendar_events,
    }


# ── MCP over Streamable HTTP ─────────────────────────────
# Claude AI connects to POST /mcp as an MCP Streamable HTTP endpoint.

def mcp_handle(method: str, req_id, params: dict) -> dict:
    """Handle a single MCP JSON-RPC request."""
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "task-manager", "version": "1.0.0"},
            },
        }
    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    elif method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            result_text = call_tool(name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result_text}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
            }
    elif method == "notifications/initialized":
        return None  # notification, no response
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP Streamable HTTP endpoint for Claude AI integration (no auth — public)."""
    body = await request.json()

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    response = mcp_handle(method, req_id, params)

    if response is None:
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return response
