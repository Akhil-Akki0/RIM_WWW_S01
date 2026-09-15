"""High-level AI service - status, prediction interface."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from core.exceptions import NoModelConfiguredError
from core.logging import get_logger

from .registry import count_models, get_model, list_models

logger = get_logger(__name__)


# Session state key for the active model
_ACTIVE_MODEL_KEY = "_ai_active_model_id"


@dataclass
class AIStatus:
    """Current status of the AI subsystem."""
    ready: bool
    message: str
    model_count: int
    active_model_id: Optional[str] = None
    active_model_name: Optional[str] = None


@dataclass
class PredictionResult:
    """A prediction from an AI model."""
    prediction: Any
    model_id: str
    model_name: str
    confidence: Optional[float]
    timestamp: str
    inputs: Dict[str, Any]


def _get_active_model_id() -> Optional[str]:
    """Read active model ID from Streamlit session state."""
    try:
        import streamlit as st
        return st.session_state.get(_ACTIVE_MODEL_KEY)
    except Exception:
        return None


def _set_active_model_id(model_id: Optional[str]) -> None:
    """Write active model ID to Streamlit session state."""
    try:
        import streamlit as st
        if model_id:
            st.session_state[_ACTIVE_MODEL_KEY] = model_id
        else:
            st.session_state.pop(_ACTIVE_MODEL_KEY, None)
    except Exception:
        pass


class AIService:
    """AI service facade."""

    def get_status(self) -> AIStatus:
        """Return current AI status."""
        n = count_models()
        active_id = _get_active_model_id()

        if n == 0:
            return AIStatus(
                ready=False,
                message="No trained model configured",
                model_count=0,
            )

        # If active_id is set but model no longer exists, clear it
        if active_id:
            model = get_model(active_id)
            if not model:
                _set_active_model_id(None)
                active_id = None

        if not active_id:
            return AIStatus(
                ready=False,
                message=f"{n} model(s) registered. Select one to activate.",
                model_count=n,
            )

        model = get_model(active_id)
        return AIStatus(
            ready=True,
            message=f"Model '{model.name}' ready",
            model_count=n,
            active_model_id=model.model_id,
            active_model_name=model.name,
        )

    def list_available_models(self):
        """List all registered models."""
        return list_models()

    def activate_model(self, model_id: str) -> None:
        """Set the active model."""
        model = get_model(model_id)
        if not model:
            raise NoModelConfiguredError(f"Model not found: {model_id}")
        _set_active_model_id(model_id)
        logger.info(f"Activated model: {model_id}")

    def deactivate_model(self) -> None:
        """Clear the active model."""
        _set_active_model_id(None)

    def predict(self, inputs: Dict[str, Any]) -> PredictionResult:
        """Run prediction with the active model."""
        active_id = _get_active_model_id()
        if not active_id:
            raise NoModelConfiguredError(
                "No model activated. Please select a model first."
            )

        model = get_model(active_id)
        if not model:
            raise NoModelConfiguredError(f"Active model missing: {active_id}")

        # Placeholder - real prediction will be added when a model exists
        return PredictionResult(
            prediction={"note": "Prediction placeholder - connect a real model"},
            model_id=model.model_id,
            model_name=model.name,
            confidence=None,
            timestamp=datetime.now().isoformat(),
            inputs=inputs,
        )