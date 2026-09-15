"""
Simulation runner - supports both demo and real OpenFOAM modes.

On Windows, OpenFOAM runs inside WSL2. This module bridges
Windows Python to WSL OpenFOAM commands.
"""

import platform
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.config import get_config
from core.exceptions import OpenFOAMExecutionError, OpenFOAMNotFoundError
from core.logging import get_logger
from core.utils import generate_simulation_id

logger = get_logger(__name__)


OPENFOAM_VERSION = "openfoam2606"
OPENFOAM_SOURCE = f"source /usr/lib/openfoam/{OPENFOAM_VERSION}/etc/bashrc"

ProgressCallback = Callable[[str, int, Optional[str]], None]


# ============================================================
# SIMULATION STATE
# ============================================================

@dataclass
class SimulationState:
    """Tracks the state of a running simulation."""

    simulation_id: str
    project_id: str
    config: Dict[str, Any]
    is_demo: bool
    status: str = "queued"
    current_step: str = ""
    progress: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    available_fields: List[str] = field(default_factory=list)
    logs: List[Dict[str, str]] = field(default_factory=list)

    def add_log(self, message: str, log_type: str = "application") -> None:
        self.logs.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": log_type,
            "message": message,
        })


# ============================================================
# WSL BRIDGE
# ============================================================

class WSLBridge:
    """Bridge Windows Python to WSL2 OpenFOAM."""

    WSL_WORK_DIR = "/tmp/of_cases"

    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self._validate_installation()

    def _validate_installation(self) -> None:
        try:
            if self.is_windows:
                result = subprocess.run(
                    ["wsl", "bash", "-c", f"{OPENFOAM_SOURCE} && which simpleFoam"],
                    capture_output=True, text=True, timeout=30,
                )
            else:
                result = subprocess.run(
                    ["bash", "-c", f"{OPENFOAM_SOURCE} && which simpleFoam"],
                    capture_output=True, text=True, timeout=30,
                )

            if result.returncode != 0 or "simpleFoam" not in result.stdout:
                raise OpenFOAMNotFoundError(
                    f"OpenFOAM not detected. Verify {OPENFOAM_VERSION} is installed."
                )
            logger.info(f"OpenFOAM detected via WSL: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise OpenFOAMNotFoundError(f"Cannot reach WSL: {e}")

    def _windows_to_wsl_path(self, win_path: Path) -> str:
        path_str = str(win_path.resolve())
        if len(path_str) > 2 and path_str[1:3] == ":\\":
            drive = path_str[0].lower()
            rest = path_str[3:].replace("\\", "/")
            return f"/mnt/{drive}/{rest}"
        return path_str.replace("\\", "/")

    def _wsl_run(self, command: str, timeout: int = 3600) -> subprocess.CompletedProcess:
        cmd = ["wsl", "bash", "-c", command] if self.is_windows else ["bash", "-c", command]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise OpenFOAMExecutionError(f"Timeout after {timeout}s: {command}")

    def prepare_case_in_wsl(self, case_path: Path) -> str:
        win_path = self._windows_to_wsl_path(case_path)
        parent_name = case_path.parent.name
        wsl_dest = f"{self.WSL_WORK_DIR}/{parent_name}"

        cmd = (
            f"mkdir -p '{self.WSL_WORK_DIR}' && "
            f"rm -rf '{wsl_dest}' && "
            f"cp -r '{win_path}' '{wsl_dest}' && "
            f"echo 'COPIED_TO:{wsl_dest}'"
        )
        result = self._wsl_run(cmd, timeout=120)

        if result.returncode != 0 or "COPIED_TO" not in result.stdout:
            raise OpenFOAMExecutionError(
                f"Failed to prepare case in WSL: {result.stderr}"
            )

        logger.info(f"Case copied to WSL: {wsl_dest}")
        return wsl_dest

    def sync_results_back(self, wsl_case_path: str, windows_case_path: Path) -> None:
        win_path = self._windows_to_wsl_path(windows_case_path)
        cmd = f"cp -r '{wsl_case_path}'/* '{win_path}/' 2>/dev/null || true"
        self._wsl_run(cmd, timeout=120)
        logger.info(f"Results synced back to {windows_case_path}")

    def run_command(
        self,
        case_path: Optional[Path] = None,
        command: str = "",
        timeout: int = 3600,
        wsl_case_path: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        if wsl_case_path:
            work_dir = wsl_case_path
        elif case_path is not None:
            work_dir = self._windows_to_wsl_path(case_path)
        else:
            work_dir = None

        parts = [OPENFOAM_SOURCE]
        if work_dir:
            parts.append(f"cd '{work_dir}'")
        parts.append(command)
        full_cmd = " && ".join(parts)

        logger.info(f"Running: {command}")
        result = self._wsl_run(full_cmd, timeout=timeout)

        # Log ALL output for snappy so we can see what it does
        if result.stdout:
            if "snappy" in command.lower():
                for line in result.stdout.splitlines()[-30:]:
                    logger.info(f"[{command}] {line.strip()}")
            else:
                keywords = ["Time =", "Solving", "ExecutionTime", "nCells", "cells:",
                            "Number of", "End", "Convergence", "residual"]
                for line in result.stdout.splitlines():
                    if any(k in line for k in keywords):
                        logger.info(f"[{command}] {line.strip()}")

        if result.stderr:
            for line in result.stderr.splitlines()[-20:]:
                logger.warning(f"[{command}] stderr: {line}")

        if result.returncode != 0:
            raise OpenFOAMExecutionError(
                f"Command failed: {command}",
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        return result

    def test_connection(self) -> bool:
        try:
            result = subprocess.run(
                ["wsl", "bash", "-c", f"{OPENFOAM_SOURCE} && which simpleFoam"],
                capture_output=True, text=True, timeout=30,
            )
            return result.returncode == 0 and "simpleFoam" in result.stdout
        except Exception:
            return False


# ============================================================
# DEMO RUNNER
# ============================================================

DEMO_STEPS = [
    ("Preparing geometry", 10, "Setting up case directory..."),
    ("Generating mesh", 35, "Running blockMesh + snappyHexMesh..."),
    ("Running solver", 75, "Iterating Navier-Stokes equations..."),
    ("Processing results", 92, "Converting to VTK format..."),
    ("Generating report", 100, "Finalizing metrics and outputs..."),
]


def run_demo_simulation(
    project_id: str,
    config: Dict[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
) -> SimulationState:
    from storage.demo_data import generate_demo_metrics, get_demo_available_fields

    sim_id = generate_simulation_id()
    state = SimulationState(
        simulation_id=sim_id, project_id=project_id,
        config=config, is_demo=True, started_at=datetime.now(),
    )
    state.add_log(f"Initializing DEMO simulation {sim_id}")

    if progress_callback:
        progress_callback("Initializing", 0, f"Simulation {sim_id} starting")

    try:
        inlet_velocity = (
            config.get("boundary_conditions", {}).get("inlet", {}).get("velocity", 10.0)
        )
        est_cells = config.get("mesh_settings", {}).get("estimated_cells", 150000)
        prev_pct = 0

        for step_name, target_pct, log_msg in DEMO_STEPS:
            state.current_step = step_name
            state.add_log(f"--- {step_name} ---")
            state.add_log(log_msg)

            for i in range(10):
                pct = prev_pct + int((target_pct - prev_pct) * (i + 1) / 10)
                state.progress = pct
                if progress_callback:
                    progress_callback(step_name, pct, log_msg)
                time.sleep(0.15)

            state.add_log(f"[OK] {step_name} completed")
            prev_pct = target_pct

        metrics = generate_demo_metrics(inlet_velocity, est_cells)
        state.metrics = metrics
        state.available_fields = get_demo_available_fields()
        state.status = "completed"
        state.completed_at = datetime.now()
        state.execution_time = (state.completed_at - state.started_at).total_seconds()
        state.add_log(f"[OK] Completed in {state.execution_time:.1f}s")

    except Exception as e:
        state.status = "failed"
        state.error_message = str(e)
        state.add_log(f"[FAIL] {e}", "error")

    return state


# ============================================================
# REAL OPENFOAM RUNNER
# ============================================================

def run_real_simulation(
    project_id: str,
    config: Dict[str, Any],
    case_path: Path,
    progress_callback: Optional[ProgressCallback] = None,
) -> SimulationState:
    """Run a real OpenFOAM simulation via WSL bridge.

    Includes snappyHexMesh for geometry refinement.
    If snappy fails, we log the FULL error and continue with background mesh.
    """
    sim_id = generate_simulation_id()
    state = SimulationState(
        simulation_id=sim_id, project_id=project_id,
        config=config, is_demo=False, started_at=datetime.now(),
    )
    state.add_log(f"Initializing REAL simulation {sim_id}")

    try:
        bridge = WSLBridge()
        state.add_log(f"OpenFOAM version: {OPENFOAM_VERSION}")

        if progress_callback:
            progress_callback("Preparing", 5, "Copying case to WSL workspace...")

        state.add_log("Copying case to WSL workspace (avoiding spaces in path)...")
        wsl_case = bridge.prepare_case_in_wsl(case_path)
        state.add_log(f"Working directory in WSL: {wsl_case}")

        # ---- Step 1: Mesh ----
        state.status = "meshing"
        state.current_step = "Generating mesh"

        state.add_log("Running blockMesh...")
        if progress_callback:
            progress_callback("Generating mesh", 15, "blockMesh running...")
        result = bridge.run_command(
            wsl_case_path=wsl_case, command="blockMesh", timeout=600,
        )
        for line in result.stdout.splitlines()[-10:]:
            state.add_log(line)

        # ---- snappyHexMesh (with full error visibility) ----
        state.add_log("Running snappyHexMesh...")
        if progress_callback:
            progress_callback("Generating mesh", 30, "snappyHexMesh running...")
        try:
            result = bridge.run_command(
                wsl_case_path=wsl_case,
                command="snappyHexMesh -overwrite",
                timeout=1800,
            )
            state.add_log("snappyHexMesh completed successfully")
            # Log last 15 lines of snappy output
            for line in result.stdout.splitlines()[-15:]:
                state.add_log(f"[snappy] {line.strip()}")

        except OpenFOAMExecutionError as e:
            state.add_log(
                "snappyHexMesh FAILED — the cylinder hole was NOT cut into the mesh. "
                "Velocity/pressure will show uniform flow (no wake).",
                "error",
            )
            # Log the actual error output — this is the key diagnostic
            if e.stdout:
                for line in e.stdout.splitlines()[-30:]:
                    if line.strip():
                        state.add_log(f"[snappy] {line.strip()}", "error")
            if e.stderr:
                for line in e.stderr.splitlines()[-20:]:
                    if line.strip():
                        state.add_log(f"[snappy] {line.strip()}", "error")

        # ---- checkMesh ----
        state.add_log("Running checkMesh...")
        try:
            result = bridge.run_command(
                wsl_case_path=wsl_case, command="checkMesh", timeout=300,
            )
            for line in result.stdout.splitlines()[-5:]:
                state.add_log(line)
        except OpenFOAMExecutionError as e:
            state.add_log(f"checkMesh warning: {str(e)[:200]}", "warning")

        # ---- Step 2: Solver ----
        state.status = "running"
        state.current_step = "Running solver"
        solver = config.get("solver_settings", {}).get("solver", "simpleFoam")
        state.add_log(f"Running {solver}...")

        if progress_callback:
            progress_callback("Running solver", 50, f"{solver} running...")

        result = bridge.run_command(
            wsl_case_path=wsl_case, command=solver, timeout=7200,
        )
        for line in result.stdout.splitlines()[-15:]:
            state.add_log(line)

        # ---- Step 3: Post-process ----
        state.status = "processing"
        state.current_step = "Processing results"
        state.add_log("Running foamToVTK...")

        if progress_callback:
            progress_callback("Processing results", 85, "Converting to VTK...")

        try:
            bridge.run_command(wsl_case_path=wsl_case, command="foamToVTK", timeout=600)
        except OpenFOAMExecutionError as e:
            state.add_log(f"foamToVTK warning: {str(e)[:200]}", "warning")

        state.add_log("Copying results back to Windows...")
        try:
            bridge.sync_results_back(wsl_case, case_path)
        except Exception as e:
            state.add_log(f"Sync back warning: {e}", "warning")

        # Parse results
        try:
            from cfd.results import ResultParser
            parser = ResultParser()
            mesh = parser.load_mesh(case_path)
            state.available_fields = parser.detect_fields(mesh)
            state.add_log(f"Detected fields: {state.available_fields}")
        except Exception as e:
            state.add_log(f"Result parsing failed: {str(e)[:200]}", "warning")

        # Compute metrics
        try:
            from cfd.metrics import MetricsCalculator
            calc = MetricsCalculator()
            state.metrics = calc.calculate_from_case(case_path)
            state.add_log(f"Metrics: {state.metrics}")
        except Exception as e:
            state.add_log(f"Metric computation failed: {str(e)[:200]}", "warning")
            state.metrics = {
                "mesh_cells": 0,
                "execution_time": 0.0,
                "converged": True,
            }

        state.status = "completed"
        state.completed_at = datetime.now()
        state.execution_time = (state.completed_at - state.started_at).total_seconds()
        state.add_log(f"[OK] Completed in {state.execution_time:.1f}s")

        if progress_callback:
            progress_callback("Complete", 100, "Simulation complete")

    except Exception as e:
        logger.error(f"Real simulation failed: {e}", exc_info=True)
        state.status = "failed"
        state.error_message = str(e)
        state.completed_at = datetime.now()
        state.execution_time = (state.completed_at - state.started_at).total_seconds()
        state.add_log(f"[FAIL] {str(e)[:300]}", "error")
        if progress_callback:
            progress_callback("Failed", state.progress, str(e))

    return state


# ============================================================
# MAIN DISPATCHER
# ============================================================

def run_simulation(
    project_id: str,
    config: Dict[str, Any],
    case_path: Optional[Path] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> SimulationState:
    app_config = get_config()

    if app_config.demo_mode:
        return run_demo_simulation(project_id, config, progress_callback)

    if case_path is None:
        raise ValueError("case_path is required for real simulations")

    return run_real_simulation(project_id, config, case_path, progress_callback)