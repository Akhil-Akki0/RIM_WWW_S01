"""AI module for the AI CFD Platform."""

from .models.base import BaseCFDModel, ModelMetadata
from .registry import (
    count_models,
    get_model,
    list_models,
    register_model,
    unregister_model,
)
from .service import AIService, AIStatus, PredictionResult

__all__ = [
    "BaseCFDModel",
    "ModelMetadata",
    "register_model",
    "list_models",
    "get_model",
    "unregister_model",
    "count_models",
    "AIService",
    "AIStatus",
    "PredictionResult",
]