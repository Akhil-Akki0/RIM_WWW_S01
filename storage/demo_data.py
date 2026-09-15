"""Demo mode data provider."""

import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pyvista as pv

from core.logging import get_logger

logger = get_logger(__name__)


def create_demo_geometry(geometry_type: str = "cylinder") -> pv.PolyData:
    if geometry_type == "cylinder":
        mesh = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), radius=0.5, height=1.0, resolution=50)
    elif geometry_type == "sphere":
        mesh = pv.Sphere(radius=0.5, center=(0, 0, 0))
    elif geometry_type == "cube":
        mesh = pv.Cube(center=(0, 0, 0), x_length=1.0, y_length=1.0, z_length=1.0)
    else:
        mesh = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), radius=0.3, height=0.2, resolution=60)
    return mesh


def create_demo_flow_field(resolution: int = 30, inlet_velocity: float = 10.0) -> pv.ImageData:
    x = np.linspace(-3, 6, resolution * 3)
    y = np.linspace(-2, 2, resolution * 2)
    z = np.linspace(-0.1, 0.1, 3)
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    r = np.sqrt(xx**2 + yy**2)
    r_safe = np.where(r < 0.5, 0.5, r)
    theta = np.arctan2(yy, xx)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    u_r = inlet_velocity * (1 - (0.5 / r_safe) ** 2) * cos_t
    u_t = -inlet_velocity * (1 + (0.5 / r_safe) ** 2) * sin_t
    u_x = u_r * cos_t - u_t * sin_t
    u_y = u_r * sin_t + u_t * cos_t
    noise = 0.05 * inlet_velocity
    u_x += np.random.normal(0, noise, u_x.shape)
    u_y += np.random.normal(0, noise, u_y.shape)
    u_mag_sq = u_x**2 + u_y**2
    pressure = 101325 - 0.5 * 1.225 * (u_mag_sq - inlet_velocity**2)
    pressure = np.where(r > 3, 101325, pressure)

    grid = pv.ImageData(
        dimensions=(len(x), len(y), len(z)),
        spacing=(x[1] - x[0], y[1] - y[0], z[1] - z[0]),
        origin=(x[0], y[0], z[0]),
    )
    n_points = len(x) * len(y) * len(z)
    velocity = np.zeros((n_points, 3))
    velocity[:, 0] = u_x.flatten()
    velocity[:, 1] = u_y.flatten()
    grid.point_data["U"] = velocity
    grid.point_data["p"] = pressure.flatten()
    grid.point_data["k"] = (0.05 * u_mag_sq).flatten()
    grid.point_data["U_magnitude"] = np.linalg.norm(velocity, axis=1)
    return grid


def generate_demo_metrics(inlet_velocity: float = 10.0, mesh_cells: int = 150000,
                          execution_time: float = 45.3) -> Dict[str, Any]:
    return {
        "max_velocity": round(inlet_velocity * 1.5, 3),
        "min_velocity": 0.0,
        "avg_velocity": round(inlet_velocity * 0.85, 3),
        "max_pressure": round(101325 + 0.5 * 1.225 * inlet_velocity**2, 2),
        "min_pressure": round(101325 - 0.6 * 1.225 * inlet_velocity**2, 2),
        "pressure_drop": round(0.6 * 1.225 * inlet_velocity**2, 2),
        "mesh_cells": mesh_cells,
        "execution_time": execution_time,
        "converged": True,
        "iterations": 342,
    }


def get_demo_available_fields() -> List[str]:
    return ["Velocity", "Pressure", "Turbulent Kinetic Energy"]


def get_demo_case_path() -> Path:
    from core.config import get_config
    config = get_config()
    demo_dir = config.data_directory / "sample_cases" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    return demo_dir


def initialize_demo_data() -> None:
    demo_dir = get_demo_case_path()
    geom_file = demo_dir / "demo_cylinder.stl"
    if not geom_file.exists():
        geometry = create_demo_geometry("cylinder")
        geometry.save(str(geom_file))
    flow_file = demo_dir / "demo_flow.vtk"
    if not flow_file.exists():
        flow = create_demo_flow_field()
        flow.save(str(flow_file))


def load_demo_flow_field() -> pv.ImageData:
    demo_dir = get_demo_case_path()
    flow_file = demo_dir / "demo_flow.vtk"
    if not flow_file.exists():
        initialize_demo_data()
    return pv.read(str(flow_file))