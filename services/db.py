"""Small storage adapter: secure Supabase cloud mode or local SQLite development mode."""
from __future__ import annotations
import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("REPTRACK_DB", str(DATA_DIR / "reptrack_local.db")))

TABLES = {
    "profiles": {"id", "username", "email", "full_name", "created_at", "body_weight_goal_kg", "weekly_goal", "preferred_unit", "theme"},
    "exercises": {"id", "owner_id", "name", "muscle_group", "target_muscles", "equipment", "difficulty", "instructions", "image_url", "video_url", "is_custom", "created_at"},
    "workout_sessions": {"id", "user_id", "workout_date", "started_at", "ended_at", "status", "muscle_groups", "notes", "duration_minutes", "created_at"},
    "workout_exercises": {"id", "user_id", "workout_id", "exercise_id", "exercise_name", "sort_order", "notes", "created_at"},
    "workout_sets": {"id", "user_id", "workout_id", "workout_exercise_id", "set_number", "weight_kg", "reps", "rpe", "completed", "created_at"},
    "body_weight_entries": {"id", "user_id", "entry_date", "weight_kg", "notes", "created_at"},
}


def _secret(name: str, default: str = "") -> str:
    value = os.getenv(name, "")
    if value:
        return value.strip()
    try:
        v = st.secrets.get(name, "")
        if v:
            return str(v).strip()
        section = st.secrets.get("supabase", {})
        aliases = {"SUPABASE_URL": "url", "SUPABASE_ANON_KEY": "anon_key", "SUPABASE_SERVICE_ROLE_KEY": "service_role_key"}
        v = section.get(aliases.get(name, name.lower()), "") if section else ""
        return str(v).strip() if v else default
    except Exception:
        return default


def cloud_config() -> dict[str, str]:
    return {
        "url": _secret("SUPABASE_URL"),
        "anon_key": _secret("SUPABASE_ANON_KEY") or _secret("SUPABASE_KEY"),
        "service_role_key": _secret("SUPABASE_SERVICE_ROLE_KEY"),
    }


def is_cloud_mode() -> bool:
    c = cloud_config()
    return bool(c["url"] and c["anon_key"])


def backend_label() -> str:
    return "Supabase cloud database" if is_cloud_mode() else "Local SQLite development database"


def supabase_client(authenticated: bool = True):
    cfg = cloud_config()
    if not (cfg["url"] and cfg["anon_key"]):
        raise RuntimeError("Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Secrets.")
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("Supabase package is missing. Install requirements.txt.") from exc
    client = create_client(cfg["url"], cfg["anon_key"])
    if authenticated:
        access = st.session_state.get("vf_access_token")
        refresh = st.session_state.get("vf_refresh_token")
        if access and refresh:
            try:
                session = client.auth.set_session(access, refresh)
                if getattr(session, "session", None):
                    _store_session(session.session)
                elif getattr(session, "access_token", None):
                    _store_session(session)
            except Exception:
                # An expired/invalid session will be handled as a signed-out state.
                pass
    return client


def admin_client():
    cfg = cloud_config()
    if not (cfg["url"] and cfg["service_role_key"]):
        return None
    from supabase import create_client
    return create_client(cfg["url"], cfg["service_role_key"])


def _store_session(session: Any) -> None:
    access = getattr(session, "access_token", None)
    refresh = getattr(session, "refresh_token", None)
    if access:
        st.session_state["vf_access_token"] = access
    if refresh:
        st.session_state["vf_refresh_token"] = refresh


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sqlite_connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_local_db() -> None:
    if is_cloud_mode():
        return
    with _sqlite_connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE, full_name TEXT NOT NULL,
            created_at TEXT NOT NULL, body_weight_goal_kg REAL, weekly_goal INTEGER DEFAULT 4,
            preferred_unit TEXT DEFAULT 'kg', theme TEXT DEFAULT 'dark'
        );
        CREATE TABLE IF NOT EXISTS local_credentials (
            user_id TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
            salt TEXT NOT NULL, password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exercises (
            id TEXT PRIMARY KEY, owner_id TEXT, name TEXT NOT NULL, muscle_group TEXT NOT NULL,
            target_muscles TEXT DEFAULT '', equipment TEXT DEFAULT '', difficulty TEXT DEFAULT 'Beginner',
            instructions TEXT DEFAULT '', image_url TEXT DEFAULT '', video_url TEXT DEFAULT '',
            is_custom INTEGER DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, workout_date TEXT NOT NULL,
            started_at TEXT NOT NULL, ended_at TEXT, status TEXT NOT NULL DEFAULT 'active',
            muscle_groups TEXT DEFAULT '', notes TEXT DEFAULT '', duration_minutes INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user_date ON workout_sessions(user_id, workout_date);
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, workout_id TEXT NOT NULL,
            exercise_id TEXT, exercise_name TEXT NOT NULL, sort_order INTEGER DEFAULT 0,
            notes TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_workout_exercises ON workout_exercises(workout_id, sort_order);
        CREATE TABLE IF NOT EXISTS workout_sets (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, workout_id TEXT NOT NULL,
            workout_exercise_id TEXT NOT NULL, set_number INTEGER NOT NULL,
            weight_kg REAL NOT NULL DEFAULT 0, reps INTEGER NOT NULL DEFAULT 0,
            rpe REAL, completed INTEGER DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sets_exercise ON workout_sets(workout_exercise_id, set_number);
        CREATE TABLE IF NOT EXISTS body_weight_entries (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, entry_date TEXT NOT NULL,
            weight_kg REAL NOT NULL, notes TEXT DEFAULT '', created_at TEXT NOT NULL,
            UNIQUE(user_id, entry_date)
        );
        CREATE INDEX IF NOT EXISTS idx_weights_user_date ON body_weight_entries(user_id, entry_date);
        """)
    seed_local_exercises()


def seed_local_exercises() -> None:
    seed_path = DATA_DIR / "exercises_seed.json"
    try:
        items = json.loads(seed_path.read_text(encoding="utf-8"))
    except Exception:
        return
    with _sqlite_connect() as con:
        n = con.execute("SELECT COUNT(*) FROM exercises WHERE owner_id IS NULL").fetchone()[0]
        if n:
            return
        for item in items:
            slug = item["name"].lower().replace(" ", "-")
            eid = str(uuid.uuid5(uuid.NAMESPACE_URL, "reptrack-exercise:" + slug))
            con.execute("""INSERT OR IGNORE INTO exercises
                (id, owner_id, name, muscle_group, target_muscles, equipment, difficulty, instructions, image_url, video_url, is_custom, created_at)
                VALUES (?, NULL, ?, ?, ?, ?, ?, ?, '', ?, 0, ?)""",
                (eid, item["name"], item["muscle_group"], item["target_muscles"], item["equipment"], item["difficulty"], item["instructions"],
                 "https://www.youtube.com/results?search_query=" + item["video_search"].replace(" ", "+"), _now()))


def init_database() -> None:
    init_local_db()


def _validate_table(table: str) -> None:
    if table not in TABLES:
        raise ValueError(f"Unsupported table: {table}")


def select_rows(table: str, filters: dict[str, Any] | None = None, order_by: str | None = None,
                descending: bool = False, limit: int | None = None) -> list[dict[str, Any]]:
    _validate_table(table)
    filters = filters or {}
    for k in filters:
        if k not in TABLES[table]: raise ValueError(f"Unsupported field: {k}")
    if is_cloud_mode():
        client = supabase_client()
        query = client.table(table).select("*")
        for key, value in filters.items():
            query = query.is_(key, "null") if value is None else query.eq(key, value)
        if order_by:
            if order_by not in TABLES[table]: raise ValueError("Unsupported order field")
            query = query.order(order_by, desc=descending)
        if limit:
            query = query.limit(int(limit))
        result = query.execute()
        return list(result.data or [])
    sql = f'SELECT * FROM "{table}"'
    clauses, params = [], []
    for key, value in filters.items():
        if value is None:
            clauses.append(f'"{key}" IS NULL')
        else:
            clauses.append(f'"{key}" = ?')
            params.append(value)
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    if order_by:
        if order_by not in TABLES[table]: raise ValueError("Unsupported order field")
        sql += f' ORDER BY "{order_by}" ' + ("DESC" if descending else "ASC")
    if limit: sql += " LIMIT " + str(int(limit))
    with _sqlite_connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def insert_row(table: str, row: dict[str, Any]) -> dict[str, Any] | None:
    _validate_table(table)
    row = dict(row)
    if "id" in TABLES[table] and "id" not in row:
        row["id"] = str(uuid.uuid4())
    if "created_at" in TABLES[table] and "created_at" not in row:
        row["created_at"] = _now()
    for k in row:
        if k not in TABLES[table]: raise ValueError(f"Unsupported field: {k}")
    if is_cloud_mode():
        res = supabase_client().table(table).insert(row).execute()
        return (res.data or [None])[0]
    cols = list(row)
    values = [int(v) if k == "completed" and isinstance(v, bool) else v for k, v in row.items()]
    placeholders = ",".join("?" for _ in cols)
    sql = f'INSERT INTO "{table}" ({",".join(chr(34)+c+chr(34) for c in cols)}) VALUES ({placeholders})'
    with _sqlite_connect() as con:
        con.execute(sql, values)
    found = select_rows(table, {"id": row["id"]}) if "id" in row else []
    return found[0] if found else row


def update_rows(table: str, filters: dict[str, Any], updates: dict[str, Any]) -> int:
    _validate_table(table)
    if not filters: raise ValueError("Refusing to update without filters")
    for k in list(filters) + list(updates):
        if k not in TABLES[table]: raise ValueError(f"Unsupported field: {k}")
    if is_cloud_mode():
        q = supabase_client().table(table).update(updates)
        for k, v in filters.items(): q = q.is_(k, "null") if v is None else q.eq(k, v)
        res = q.execute()
        return len(res.data or [])
    if not updates: return 0
    set_clause = ",".join(f'"{k}" = ?' for k in updates)
    where, params = [], list(updates.values())
    for k, v in filters.items():
        if v is None: where.append(f'"{k}" IS NULL')
        else: where.append(f'"{k}" = ?'); params.append(v)
    with _sqlite_connect() as con:
        cur = con.execute(f'UPDATE "{table}" SET {set_clause} WHERE ' + " AND ".join(where), params)
        return cur.rowcount


def delete_rows(table: str, filters: dict[str, Any]) -> int:
    _validate_table(table)
    if not filters: raise ValueError("Refusing to delete without filters")
    for k in filters:
        if k not in TABLES[table]: raise ValueError(f"Unsupported field: {k}")
    if is_cloud_mode():
        q = supabase_client().table(table).delete()
        for k, v in filters.items(): q = q.is_(k, "null") if v is None else q.eq(k, v)
        res = q.execute()
        return len(res.data or [])
    where, params = [], []
    for k, v in filters.items():
        if v is None: where.append(f'"{k}" IS NULL')
        else: where.append(f'"{k}" = ?'); params.append(v)
    with _sqlite_connect() as con:
        cur = con.execute(f'DELETE FROM "{table}" WHERE ' + " AND ".join(where), params)
        return cur.rowcount


def upsert_row(table: str, row: dict[str, Any], conflict_fields: str) -> dict[str, Any] | None:
    _validate_table(table)
    for k in row:
        if k not in TABLES[table]: raise ValueError(f"Unsupported field: {k}")
    if "id" in TABLES[table] and "id" not in row: row["id"] = str(uuid.uuid4())
    if "created_at" in TABLES[table] and "created_at" not in row: row["created_at"] = _now()
    if is_cloud_mode():
        res = supabase_client().table(table).upsert(row, on_conflict=conflict_fields).execute()
        return (res.data or [None])[0]
    cols = list(row)
    update_cols = [k for k in cols if k not in conflict_fields.split(",")]
    vals = [int(v) if k == "completed" and isinstance(v, bool) else v for k, v in row.items()]
    updates = ",".join(f'"{c}"=excluded."{c}"' for c in update_cols)
    sql = f'INSERT INTO "{table}" ({",".join(chr(34)+c+chr(34) for c in cols)}) VALUES ({",".join("?" for _ in cols)}) ON CONFLICT ({conflict_fields}) DO UPDATE SET {updates}'
    with _sqlite_connect() as con: con.execute(sql, vals)
    filter_values = {k: row[k] for k in conflict_fields.split(",")}
    found = select_rows(table, filter_values)
    return found[0] if found else row


def register_local_user(username: str, email: str, full_name: str, salt: str, password_hash: str) -> dict[str, Any]:
    if is_cloud_mode(): raise RuntimeError("Local registration is unavailable in cloud mode")
    uid = str(uuid.uuid4())
    profile = {"id": uid, "username": username, "email": email.lower(), "full_name": full_name,
               "created_at": _now(), "body_weight_goal_kg": None, "weekly_goal": 4, "preferred_unit": "kg", "theme": "dark"}
    with _sqlite_connect() as con:
        con.execute("INSERT INTO profiles (id, username, email, full_name, created_at, body_weight_goal_kg, weekly_goal, preferred_unit, theme) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    tuple(profile[k] for k in ("id", "username", "email", "full_name", "created_at", "body_weight_goal_kg", "weekly_goal", "preferred_unit", "theme")))
        con.execute("INSERT INTO local_credentials (user_id, salt, password_hash) VALUES (?, ?, ?)", (uid, salt, password_hash))
    return profile


def verify_local_credentials(identifier: str, password_hash: str) -> dict[str, Any] | None:
    if is_cloud_mode(): return None
    with _sqlite_connect() as con:
        row = con.execute("""SELECT p.*, c.salt, c.password_hash FROM profiles p
            JOIN local_credentials c ON c.user_id=p.id WHERE lower(p.email)=lower(?) OR lower(p.username)=lower(?)""",
            (identifier.strip(), identifier.strip())).fetchone()
    if not row or row["password_hash"] != password_hash: return None
    return {k: row[k] for k in TABLES["profiles"]}


def local_salt(identifier: str) -> str | None:
    with _sqlite_connect() as con:
        row = con.execute("""SELECT c.salt FROM profiles p JOIN local_credentials c ON c.user_id=p.id
            WHERE lower(p.email)=lower(?) OR lower(p.username)=lower(?)""", (identifier.strip(), identifier.strip())).fetchone()
    return row["salt"] if row else None


def resolve_username_email(username: str) -> str | None:
    """Resolve username without returning its email to the UI. Requires server-only service role key."""
    cfg = cloud_config()
    if not (cfg["url"] and cfg["service_role_key"]):
        return None
    try:
        client = admin_client()
        res = client.table("profiles").select("email").ilike("username", username.strip()).limit(1).execute()
        return res.data[0]["email"] if res.data else None
    except Exception:
        return None
