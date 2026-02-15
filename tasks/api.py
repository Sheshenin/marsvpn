"""Task management API server with MCP support."""

import json
import os
import uuid
from datetime import datetime
from functools import wraps

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from tasks import db
from tasks.mcp_server import TOOLS, call_tool

API_TOKEN = os.environ.get("TASKS_API_TOKEN", "")

app = FastAPI(title="Task Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {"id": pid, "name": project.name}


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, authorization: str = Header(None)):
    verify_token(authorization)
    db.delete_project(project_id)
    return {"deleted": project_id}


# ── Overview ──────────────────────────────────────────────

@app.get("/overview")
def daily_overview(authorization: str = Header(None)):
    verify_token(authorization)
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": db.task_summary(),
        "overdue": db.overdue_tasks(),
        "due_today": db.tasks_due_today(),
        "inbox": db.list_inbox(),
        "active": db.list_tasks(status="active"),
        "waiting": db.list_tasks(status="waiting"),
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
async def mcp_endpoint(request: Request, authorization: str = Header(None)):
    """MCP Streamable HTTP endpoint for Claude AI integration."""
    verify_token(authorization)
    body = await request.json()

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    response = mcp_handle(method, req_id, params)

    if response is None:
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return response
