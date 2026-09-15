"""Configuration management for the AI CFD Platform."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    openfoam_path: Optional[str] = None
    data_directory: Path = field(default_factory=lambda: Path("data"))
    model_directory: Path = field(default_factory=lambda: Path("data/models"))
    database_path: Path = field(default_factory=lambda: Path("data/cfd_platform.db"))
    log_file: Path = field(default_factory=lambda: Path("data/logs/app.log"))
    demo_mode: bool = False
    debug: bool = False
    log_level: str = "INFO"
    default_solver: str = "simpleFoam"
    max_iterations: int = 1000
    convergence_tolerance: float = 1e-4

    def __post_init__(self):
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.model_directory.mkdir(parents=True, exist_ok=True)
        (self.data_directory / "projects").mkdir(exist_ok=True)
        (self.data_directory / "simulations").mkdir(exist_ok=True)
        (self.data_directory / "temp").mkdir(exist_ok=True)
        (self.data_directory / "logs").mkdir(exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            openfoam_path=os.getenv("OPENFOAM_PATH") or None,
            data_directory=Path(os.getenv("DATA_DIRECTORY", "data")),
            model_directory=Path(os.getenv("MODEL_DIRECTORY", "data/models")),
            database_path=Path(os.getenv("DATABASE_PATH", "data/cfd_platform.db")),
            log_file=Path(os.getenv("LOG_FILE", "data/logs/app.log")),
            demo_mode=os.getenv("DEMO_MODE", "false").lower() == "true",
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    global _config
    _config = None