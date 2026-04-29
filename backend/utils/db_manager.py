"""
PostgreSQL persistence for healing runs (replaces hosted Supabase/PostgREST).
Set DATABASE_URL, e.g. postgresql://user:pass@host:5432/dbname
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json


def _env_truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


class DbManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self) -> None:
        # Local dev on laptop while DATABASE_URL points at VPC-only RDS — ignore Postgres entirely.
        if _env_truthy(os.environ.get("ARBITER_LOCAL_DEV")):
            self.dsn = None
            self.enabled = False
            print(
                "ARBITER_LOCAL_DEV is set — PostgreSQL disabled locally (DATABASE_URL ignored). "
                "Unset for EC2/production. Use backend/.env.local for this flag."
            )
            return

        self.dsn: Optional[str] = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        if self.dsn:
            self.enabled = True
        else:
            print("WARNING: DATABASE_URL not set. Run logging and history disabled.")
            self.enabled = False

    def _connect_kw(self) -> dict:
        """Short TCP/connect timeout avoids hanging forever when RDS is VPC-only from local dev."""
        raw = os.environ.get("PG_CONNECT_TIMEOUT", "8")
        try:
            sec = max(2, min(120, int(raw)))
        except ValueError:
            sec = 8
        return {"connect_timeout": sec}

    def init_schema(self) -> None:
        """Creates tables if they do not exist (PostgreSQL 13+ for gen_random_uuid)."""
        if not self.enabled or not self.dsn:
            return
        if os.environ.get("SKIP_PG_INIT", "").strip().lower() in ("1", "true", "yes"):
            print("SKIP_PG_INIT set — skipping PostgreSQL schema init.")
            return
        stmts = [
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_name TEXT,
                team_name TEXT,
                leader_name TEXT,
                target_repo TEXT,
                status TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                final_score INTEGER,
                duration DOUBLE PRECISION,
                pr_url TEXT,
                branch_name TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS node_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
                node_name TEXT NOT NULL,
                log_type TEXT NOT NULL,
                content JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_node_logs_run_id ON node_logs(run_id)",
        ]
        try:
            with psycopg.connect(self.dsn, **self._connect_kw()) as conn:
                for sql in stmts:
                    conn.execute(sql)
        except Exception as e:
            print(
                f"DbManager Warning (init_schema): {e}\n"
                "If developing locally: RDS may be reachable only inside your VPC — run the API on EC2, "
                "or set SKIP_PG_INIT=true, or temporarily remove DATABASE_URL. "
                "Set PG_CONNECT_TIMEOUT (seconds) if connections feel slow.\n"
            )

    def create_run(
        self,
        run_name: str,
        target_repo: str,
        team_name: str = "",
        leader_name: str = "",
    ) -> Optional[str]:
        if not self.enabled or not self.dsn:
            return None
        data = (
            run_name,
            team_name or None,
            leader_name or None,
            target_repo,
            "PENDING",
            datetime.now(timezone.utc),
        )
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, **self._connect_kw()) as conn:
                row = conn.execute(
                    """
                    INSERT INTO agent_runs (run_name, team_name, leader_name, target_repo, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    data,
                ).fetchone()
            if row and row.get("id"):
                return str(row["id"])
        except Exception as e:
            print(f"DbManager Error (create_run): {e}")
        return None

    def update_node_status(
        self, run_id: str, node: str, log_type: str, content: Dict[str, Any]
    ) -> None:
        if not self.enabled or not self.dsn or not run_id:
            return
        try:
            payload = (
                run_id,
                node,
                log_type,
                Json(content),
                datetime.now(timezone.utc),
            )
            with psycopg.connect(self.dsn, **self._connect_kw()) as conn:
                conn.execute(
                    """
                    INSERT INTO node_logs (run_id, node_name, log_type, content, created_at)
                    VALUES (%s::uuid, %s, %s, %s, %s)
                    """,
                    payload,
                )
        except Exception as e:
            print(f"DbManager Error (update_node_status): {e}")

    def finalize_run(
        self,
        run_id: str,
        score: int,
        duration: float,
        status: str,
        pr_url: Optional[str] = None,
        branch_name: Optional[str] = None,
    ) -> None:
        if not self.enabled or not self.dsn or not run_id:
            return
        try:
            with psycopg.connect(self.dsn, **self._connect_kw()) as conn:
                conn.execute(
                    """
                    UPDATE agent_runs SET
                        final_score = %s,
                        duration = %s,
                        status = %s,
                        pr_url = %s,
                        branch_name = %s
                    WHERE id = %s::uuid
                    """,
                    (
                        score,
                        duration,
                        status,
                        pr_url,
                        branch_name,
                        run_id,
                    ),
                )
        except Exception as e:
            print(f"DbManager Error (finalize_run): {e}")

    def get_previous_fix(self, bug_type: str, description: str) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self.dsn:
            return None
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, **self._connect_kw()) as conn:
                rows = conn.execute(
                    """
                    SELECT content FROM node_logs
                    WHERE log_type = 'FIX_APPLIED'
                    """
                ).fetchall()

            curr_desc = description.lower()
            curr_words = set(curr_desc.split())

            for row in rows or []:
                raw = row.get("content") or {}
                content = raw if isinstance(raw, dict) else {}
                if content.get("bug_type") != bug_type:
                    continue
                past_desc = str(content.get("description", "")).lower()
                past_words = set(past_desc.split())
                common = past_words.intersection(curr_words)
                if len(common) / max(len(curr_words), 1) > 0.5:
                    return content
            return None
        except Exception as e:
            print(f"DbManager Error (get_previous_fix): {e}")
            return None

    # --- REST helpers for frontend ---

    def count_runs(self) -> int:
        if not self.enabled or not self.dsn:
            return 0
        try:
            with psycopg.connect(self.dsn, **self._connect_kw()) as conn:
                row = conn.execute("SELECT COUNT(*) AS c FROM agent_runs").fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            print(f"DbManager Error (count_runs): {e}")
            return 0

    def last_run_status(self) -> Optional[str]:
        if not self.enabled or not self.dsn:
            return None
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, **self._connect_kw()) as conn:
                row = conn.execute(
                    """
                    SELECT status FROM agent_runs
                    ORDER BY created_at DESC NULLS LAST
                    LIMIT 1
                    """
                ).fetchone()
            return row["status"] if row else None
        except Exception as e:
            print(f"DbManager Error (last_run_status): {e}")
            return None

    def list_runs(self) -> List[Dict[str, Any]]:
        if not self.enabled or not self.dsn:
            return []
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, **self._connect_kw()) as conn:
                rows = conn.execute(
                    """
                    SELECT id, run_name, team_name, leader_name, target_repo, status,
                           created_at, final_score, duration, pr_url, branch_name
                    FROM agent_runs
                    ORDER BY created_at DESC NULLS LAST
                    """
                ).fetchall()
            return [_serialize_run(r) for r in rows]
        except Exception as e:
            print(f"DbManager Error (list_runs): {e}")
            return []

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self.dsn:
            return None
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, **self._connect_kw()) as conn:
                row = conn.execute(
                    """
                    SELECT id, run_name, team_name, leader_name, target_repo, status,
                           created_at, final_score, duration, pr_url, branch_name
                    FROM agent_runs WHERE id = %s::uuid
                    """,
                    (run_id,),
                ).fetchone()
            return _serialize_run(row) if row else None
        except Exception as e:
            print(f"DbManager Error (get_run): {e}")
            return None

    def list_logs_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        if not self.enabled or not self.dsn:
            return []
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, **self._connect_kw()) as conn:
                rows = conn.execute(
                    """
                    SELECT id, run_id, node_name, log_type, content, created_at
                    FROM node_logs
                    WHERE run_id = %s::uuid
                    ORDER BY created_at ASC NULLS LAST
                    """,
                    (run_id,),
                ).fetchall()
            out = []
            for r in rows or []:
                rid = r.get("id")
                run_uuid = r.get("run_id")
                out.append(
                    {
                        "id": str(rid) if rid is not None else None,
                        "run_id": str(run_uuid) if run_uuid is not None else None,
                        "node_name": r.get("node_name"),
                        "log_type": r.get("log_type"),
                        "content": r.get("content"),
                        "created_at": _iso(r.get("created_at")),
                    }
                )
            return out
        except Exception as e:
            print(f"DbManager Error (list_logs_for_run): {e}")
            return []


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _serialize_run(r: Dict[str, Any]) -> Dict[str, Any]:
    if not r:
        return {}
    rid = r.get("id")
    return {
        "id": str(rid) if rid is not None else None,
        "run_name": r.get("run_name"),
        "team_name": r.get("team_name"),
        "leader_name": r.get("leader_name"),
        "target_repo": r.get("target_repo"),
        "status": r.get("status"),
        "created_at": _iso(r.get("created_at")),
        "final_score": r.get("final_score"),
        "duration": r.get("duration"),
        "pr_url": r.get("pr_url"),
        "branch_name": r.get("branch_name"),
    }
