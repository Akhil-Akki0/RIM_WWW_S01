"""Abstract base class for CFD AI models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn


@dataclass
class ModelMetadata:
    """Metadata describing a trained AI model."""
    model_id: str
    name: str
    version: str
    model_type: str
    description: str = ""
    input_features: List[str] = field(default_factory=list)
    output_features: List[str] = field(default_factory=list)
    training_metrics: Dict[str, float] = field(default_factory=dict)
    validation_metrics: Dict[str, float] = field(default_factory=dict)
    trained_on: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""


class BaseCFDModel(ABC, nn.Module):
    """Abstract base for CFD surrogate models."""

    def __init__(self, metadata: Optional[ModelMetadata] = None):
        super().__init__()
        self._metadata = metadata

    @property
    def metadata(self) -> Optional[ModelMetadata]:
        return self._metadata

    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass."""
        pass

    @abstractmethod
    def predict(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Make a prediction with metadata."""
        pass

    def save(self, path: str) -> None:
        """Save model weights and metadata."""
        torch.save({
            "state_dict": self.state_dict(),
            "metadata": self._metadata.__dict__ if self._metadata else None,
        }, path)

    def load(self, path: str) -> None:
        """Load model weights and metadata."""
        checkpoint = torch.load(path, map_location="cpu")
        self.load_state_dict(checkpoint["state_dict"])
        if checkpoint.get("metadata"):
            self._metadata = ModelMetadata(**checkpoint["metadata"])