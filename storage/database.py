"""SQLite database management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from core.config import get_config
from core.logging import get_logger

logger = get_logger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    cfd_type TEXT NOT NULL,
    fluid_type TEXT,
    simulation_type TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS geometries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    format TEXT,
    validation_status TEXT DEFAULT 'pending',
    validation_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS simulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id TEXT UNIQUE NOT NULL,
    project_id TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    solver TEXT,
    case_path TEXT,
    config TEXT,
    metrics TEXT,
    available_fields TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time REAL,
    error_message TEXT,
    is_demo INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS simulation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id TEXT NOT NULL,
    log_type TEXT DEFAULT 'application',
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
);

CREATE INDEX IF NOT EXISTS idx_simulations_project ON simulations(project_id);
CREATE INDEX IF NOT EXISTS idx_simulations_status ON simulations(status);
CREATE INDEX IF NOT EXISTS idx_logs_simulation ON simulation_logs(simulation_id);
"""


def get_db_path() -> Path:
    return get_config().database_path


def init_database() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info(f"Database initialized at {db_path}")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row else {}