"""Project CRUD operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logging import get_logger
from core.utils import generate_project_id

from .database import get_connection, row_to_dict

logger = get_logger(__name__)


# ============================================================
# PROJECT CRUD
# ============================================================


def create_project(
    name: str,
    description: str = "",
    cfd_type: str = "External Aerodynamics",
    fluid_type: str = "Air",
    simulation_type: str = "Steady State",
) -> Dict[str, Any]:
    """Create a new project."""
    project_id = generate_project_id()

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO projects
               (project_id, name, description, cfd_type, fluid_type, simulation_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, name, description, cfd_type, fluid_type, simulation_type),
        )
        cursor = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?", (project_id,)
        )
        row = cursor.fetchone()

    logger.info(f"Created project: {project_id}")
    return row_to_dict(row)


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get a single project by ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?", (project_id,)
        )
        row = cursor.fetchone()
    return row_to_dict(row) if row else None


def list_projects(limit: int = 100) -> List[Dict[str, Any]]:
    """List all projects, newest first."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
    return [row_to_dict(row) for row in rows]


def count_projects() -> int:
    """Count total projects."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as count FROM projects")
        row = cursor.fetchone()
    return row["count"] if row else 0


def update_project(project_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Update project fields."""
    allowed = {
        "name",
        "description",
        "cfd_type",
        "fluid_type",
        "simulation_type",
        "status",
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed}

    if not updates:
        return get_project(project_id)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [project_id]

    with get_connection() as conn:
        conn.execute(f"UPDATE projects SET {set_clause} WHERE project_id = ?", values)

    return get_project(project_id)


def delete_project(project_id: str) -> bool:
    """Delete a project and all related records."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM simulation_logs WHERE simulation_id IN "
            "(SELECT simulation_id FROM simulations WHERE project_id = ?)",
            (project_id,),
        )
        conn.execute("DELETE FROM simulations WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM geometries WHERE project_id = ?", (project_id,))
        cursor = conn.execute(
            "DELETE FROM projects WHERE project_id = ?", (project_id,)
        )
    return cursor.rowcount > 0


# ============================================================
# GEOMETRY LINKING
# ============================================================


def save_geometry_record(
    project_id: str,
    filename: str,
    original_filename: str,
    file_path: str,
    file_size: int,
    file_format: str,
    validation_status: str = "valid",
    validation_message: str = "",
) -> Dict[str, Any]:
    """Save a geometry record linked to a project."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO geometries
                (project_id, filename, original_filename, file_path,
                 file_size, format, validation_status, validation_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                filename,
                original_filename,
                file_path,
                file_size,
                file_format,
                validation_status,
                validation_message,
            ),
        )
        cursor = conn.execute(
            "SELECT * FROM geometries WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        )
        row = cursor.fetchone()

    logger.info(f"Saved geometry record for project {project_id}: {filename}")
    return row_to_dict(row)


def get_geometry(project_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent geometry for a project."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM geometries WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        )
        row = cursor.fetchone()
    return row_to_dict(row) if row else None


def list_geometries(project_id: str) -> List[Dict[str, Any]]:
    """List all geometries for a project."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM geometries WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        rows = cursor.fetchall()
    return [row_to_dict(row) for row in rows]


def delete_geometry_record(project_id: str) -> None:
    """Delete all geometry records for a project."""
    with get_connection() as conn:
        conn.execute("DELETE FROM geometries WHERE project_id = ?", (project_id,))
    logger.info(f"Deleted all geometry records for project {project_id}")
