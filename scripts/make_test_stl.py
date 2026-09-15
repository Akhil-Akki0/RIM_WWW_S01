"""Generate proper binary STL files for OpenFOAM testing.

OpenFOAM's snappyHexMesh requires valid binary STL files with a proper
80-byte header that does NOT start with "solid". PyVista's default
save() produces files with a non-standard header that OpenFOAM rejects.
This script writes raw binary STL files manually.
"""

from pathlib import Path

import numpy as np
import pyvista as pv


def _save_as_binary_stl(mesh: pv.PolyData, output_path: Path) -> int:
    """Save a PyVista mesh as a proper binary STL file.

    Returns:
        Number of triangles written.
    """
    mesh = mesh.triangulate()
    points = np.asarray(mesh.points, dtype=np.float32)
    faces = mesh.faces.reshape(-1, 4)[:, 1:]
    n_triangles = len(faces)

    with open(output_path, "wb") as f:
        # 80-byte header. Must NOT start with "solid".
        header = b"Binary STL - AI CFD Platform".ljust(80, b" ")
        f.write(header)

        # Triangle count (uint32 LE)
        f.write(np.uint32(n_triangles).tobytes())

        # Each triangle: normal (12B) + 3 verts (36B) + attr (2B) = 50B
        for tri_idx in faces:
            v0 = points[tri_idx[0]]
            v1 = points[tri_idx[1]]
            v2 = points[tri_idx[2]]

            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm

            f.write(np.asarray(normal, dtype=np.float32).tobytes())
            f.write(np.asarray(v0, dtype=np.float32).tobytes())
            f.write(np.asarray(v1, dtype=np.float32).tobytes())
            f.write(np.asarray(v2, dtype=np.float32).tobytes())
            f.write(np.uint16(0).tobytes())

    return n_triangles


def create_test_cylinder(output_dir: str = "data/sample_cases") -> Path:
    """Cylinder in XY plane (vertical axis = Z), radius 0.5, height 2.0.

    Height 2.0 > domain thickness 0.2 so the cylinder spans the entire
    front-to-back depth of the mesh - snappy can cut a proper hole.
    """
    output_path = Path(output_dir) / "test_cylinder.stl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cylinder = pv.Cylinder(
        center=(0, 0, 0),
        direction=(0, 0, 1),
        radius=0.5,
        height=2.0,
        resolution=64,
        capping=True,
    )
    n = _save_as_binary_stl(cylinder, output_path)
    print(f"[OK] test_cylinder.stl : {n} triangles")
    return output_path


def create_test_airfoil(output_dir: str = "data/sample_cases") -> Path:
    output_path = Path(output_dir) / "test_airfoil.stl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sphere = pv.Sphere(radius=0.5, center=(0, 0, 0))
    n = _save_as_binary_stl(sphere, output_path)
    print(f"[OK] test_airfoil.stl  : {n} triangles")
    return output_path


def create_test_cube(output_dir: str = "data/sample_cases") -> Path:
    output_path = Path(output_dir) / "test_cube.stl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cube = pv.Cube(center=(0, 0, 0), x_length=1.0, y_length=1.0, z_length=2.0)
    n = _save_as_binary_stl(cube, output_path)
    print(f"[OK] test_cube.stl     : {n} triangles")
    return output_path


if __name__ == "__main__":
    print("Generating binary STL test files...\n")
    create_test_cylinder()
    create_test_airfoil()
    create_test_cube()
    print("\n[DONE] All binary STLs written.")