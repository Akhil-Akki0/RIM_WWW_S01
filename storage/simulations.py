"""Simulation CRUD operations."""

import json
from typing import Any, Dict, List, Optional

from core.logging import get_logger
from core.utils import generate_simulation_id

from .database import get_connection, row_to_dict

logger = get_logger(__name__)


def create_simulation(project_id: str, solver: str = "simpleFoam",
                      config: Optional[Dict[str, Any]] = None, is_demo: bool = False) -> Dict[str, Any]:
    simulation_id = generate_simulation_id()
    config_json = json.dumps(config) if config else None
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO simulations (simulation_id, project_id, solver, config, is_demo, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (simulation_id, project_id, solver, config_json, int(is_demo), "queued"),
        )
        cursor = conn.execute("SELECT * FROM simulations WHERE simulation_id = ?", (simulation_id,))
        row = cursor.fetchone()
    logger.info(f"Created simulation: {simulation_id}")
    return row_to_dict(row)


def get_simulation(simulation_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM simulations WHERE simulation_id = ?", (simulation_id,))
        row = cursor.fetchone()
    return row_to_dict(row) if row else None


def list_simulations(project_id: Optional[str] = None, status: Optional[str] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
    query = "SELECT * FROM simulations WHERE 1=1"
    params: List[Any] = []
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
    return [row_to_dict(row) for row in rows]


def count_simulations(status: Optional[str] = None) -> int:
    query = "SELECT COUNT(*) as count FROM simulations"
    params: List[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        row = cursor.fetchone()
    return row["count"] if row else 0


def update_simulation_status(simulation_id: str, status: str,
                              error_message: Optional[str] = None) -> None:
    with get_connection() as conn:
        if status in ("preparing", "meshing", "running"):
            conn.execute(
                """UPDATE simulations SET status = ?, error_message = ?,
                   started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                   WHERE simulation_id = ?""",
                (status, error_message, simulation_id),
            )
        elif status in ("completed", "failed", "cancelled"):
            conn.execute(
                """UPDATE simulations SET status = ?, error_message = ?,
                   completed_at = CURRENT_TIMESTAMP WHERE simulation_id = ?""",
                (status, error_message, simulation_id),
            )
        else:
            conn.execute("UPDATE simulations SET status = ? WHERE simulation_id = ?",
                         (status, simulation_id))


def update_simulation_results(simulation_id: str, metrics: Dict[str, Any],
                               available_fields: List[str], execution_time: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE simulations SET metrics = ?, available_fields = ?, execution_time = ?
               WHERE simulation_id = ?""",
            (json.dumps(metrics), json.dumps(available_fields), execution_time, simulation_id),
        )


def append_log(simulation_id: str, content: str, log_type: str = "application") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO simulation_logs (simulation_id, log_type, content) VALUES (?, ?, ?)",
            (simulation_id, log_type, content),
        )


def get_logs(simulation_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM simulation_logs WHERE simulation_id = ? ORDER BY timestamp ASC",
            (simulation_id,),
        )
        rows = cursor.fetchall()
    return [row_to_dict(row) for row in rows]


def delete_simulation(simulation_id: str) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM simulation_logs WHERE simulation_id = ?", (simulation_id,))
        cursor = conn.execute("DELETE FROM simulations WHERE simulation_id = ?", (simulation_id,))
    return cursor.rowcount > 0