"""Task database module — CRUD operations for task management."""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database from schema.sql."""
    conn = get_connection()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.close()


# ── Projects ──────────────────────────────────────────────

def create_project(name: str, description: str = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (name, description),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def list_projects() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_project(project_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


# ── Tasks ─────────────────────────────────────────────────

def add_task(
    title: str,
    details: str = None,
    project_id: int = None,
    status: str = "active",
    deadline: str = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO tasks (title, details, project_id, status, deadline)
           VALUES (?, ?, ?, ?, ?)""",
        (title, details, project_id, status, deadline),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def get_task(task_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT t.*, p.name as project_name
           FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
           WHERE t.id = ?""",
        (task_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_tasks(
    status: str = None,
    project_id: int = None,
    include_done: bool = False,
) -> list[dict]:
    query = """SELECT t.*, p.name as project_name
               FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
               WHERE 1=1"""
    params = []

    if status:
        query += " AND t.status = ?"
        params.append(status)
    elif not include_done:
        query += " AND t.status NOT IN ('done', 'cancelled')"

    if project_id:
        query += " AND t.project_id = ?"
        params.append(project_id)

    query += " ORDER BY t.deadline IS NULL, t.deadline, t.created_at"

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_task(task_id: int, **fields) -> bool:
    allowed = {"title", "details", "project_id", "status", "deadline"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    updates["updated_at"] = datetime.now().isoformat(timespec="seconds")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]

    conn = get_connection()
    cur = conn.execute(
        f"UPDATE tasks SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def complete_task(task_id: int) -> bool:
    return update_task(task_id, status="done")


def delete_task(task_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# ── Queries for daily overview ────────────────────────────

def tasks_due_today() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        """SELECT t.*, p.name as project_name
           FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
           WHERE t.deadline = ? AND t.status IN ('active', 'waiting')
           ORDER BY t.created_at""",
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def overdue_tasks() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        """SELECT t.*, p.name as project_name
           FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
           WHERE t.deadline < ? AND t.status IN ('active', 'waiting')
           ORDER BY t.deadline""",
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def task_summary() -> dict:
    """Return counts by status for a quick overview."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
    ).fetchall()
    conn.close()
    return {r["status"]: r["cnt"] for r in rows}


# Auto-init on first import
if not DB_PATH.exists():
    init_db()
