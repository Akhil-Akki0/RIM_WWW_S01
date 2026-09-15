"""Custom exceptions."""

from typing import Any, Dict, Optional


class CFDPlatformError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(CFDPlatformError):
    pass


class GeometryError(CFDPlatformError):
    pass


class MeshError(CFDPlatformError):
    pass


class OpenFOAMError(CFDPlatformError):
    pass


class OpenFOAMNotFoundError(OpenFOAMError):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "OpenFOAM is not installed or configured.")


class OpenFOAMExecutionError(OpenFOAMError):
    def __init__(self, message: str, stdout: str = "", stderr: str = "", return_code: int = -1):
        super().__init__(message, details={"return_code": return_code})
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code


class SimulationError(CFDPlatformError):
    pass


class AIError(CFDPlatformError):
    pass


class NoModelConfiguredError(AIError):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "No trained AI model is configured.")


class ModulusNotAvailableError(AIError):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "NVIDIA Modulus is not installed.")


class StorageError(CFDPlatformError):
    pass


class ProjectNotFoundError(StorageError):
    pass


class SimulationNotFoundError(StorageError):
    pass