"""Model registry — track available trained AI models."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import get_config
from core.logging import get_logger
from core.utils import generate_model_id

from .models.base import ModelMetadata

logger = get_logger(__name__)


def _registry_dir() -> Path:
    """Directory where model metadata is stored."""
    config = get_config()
    d = config.model_directory
    d.mkdir(parents=True, exist_ok=True)
    return d


def _registry_file() -> Path:
    """JSON file that lists all registered models."""
    return _registry_dir() / "registry.json"


def _load_registry() -> Dict[str, Any]:
    """Load the registry from disk."""
    rf = _registry_file()
    if not rf.exists():
        return {"models": []}
    try:
        with open(rf, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load registry: {e}")
        return {"models": []}


def _save_registry(data: Dict[str, Any]) -> None:
    """Save the registry to disk."""
    rf = _registry_file()
    with open(rf, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ============================================================
# PUBLIC API
# ============================================================

def register_model(metadata: ModelMetadata) -> None:
    """Register a model's metadata."""
    reg = _load_registry()
    # Replace if exists, otherwise append
    reg["models"] = [
        m for m in reg["models"] if m.get("model_id") != metadata.model_id
    ]
    reg["models"].append(asdict(metadata))
    _save_registry(reg)
    logger.info(f"Registered model: {metadata.model_id}")


def list_models() -> List[ModelMetadata]:
    """List all registered models."""
    reg = _load_registry()
    models = []
    for m in reg.get("models", []):
        try:
            models.append(ModelMetadata(**m))
        except Exception as e:
            logger.warning(f"Invalid model metadata: {e}")
    return models


def get_model(model_id: str) -> Optional[ModelMetadata]:
    """Get a model by ID."""
    for m in list_models():
        if m.model_id == model_id:
            return m
    return None


def unregister_model(model_id: str) -> bool:
    """Remove a model from the registry."""
    reg = _load_registry()
    before = len(reg["models"])
    reg["models"] = [m for m in reg["models"] if m.get("model_id") != model_id]
    after = len(reg["models"])
    _save_registry(reg)
    return after < before


def count_models() -> int:
    """Return number of registered models."""
    return len(list_models())