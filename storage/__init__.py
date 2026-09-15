"""Storage layer."""

from .database import get_connection, init_database
from .projects import (
    count_projects,
    create_project,
    delete_geometry_record,
    delete_project,
    get_geometry,
    get_project,
    list_geometries,
    list_projects,
    save_geometry_record,
    update_project,
)
from .simulations import (
    append_log,
    count_simulations,
    create_simulation,
    delete_simulation,
    get_logs,
    get_simulation,
    list_simulations,
    update_simulation_results,
    update_simulation_status,
)

__all__ = [
    "get_connection", "init_database",
    # Projects
    "create_project", "get_project", "list_projects", "count_projects",
    "update_project", "delete_project",
    # Geometries
    "save_geometry_record", "get_geometry", "list_geometries", "delete_geometry_record",
    # Simulations
    "create_simulation", "get_simulation", "list_simulations",
    "count_simulations", "update_simulation_status", "update_simulation_results",
    "delete_simulation", "append_log", "get_logs",
]