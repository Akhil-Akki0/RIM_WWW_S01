"""Generate OpenFOAM case files from user configuration."""

import shutil
from pathlib import Path
from typing import Any, Dict

from core.logging import get_logger

logger = get_logger(__name__)


class CaseGenerator:
    """Generate OpenFOAM case directory structure and files."""

    def generate(
        self,
        case_path: Path,
        geometry_path: Path,
        config: Dict[str, Any],
    ) -> Path:
        """Generate complete OpenFOAM case."""
        case_path.mkdir(parents=True, exist_ok=True)
        (case_path / "0").mkdir(exist_ok=True)
        (case_path / "constant").mkdir(exist_ok=True)
        (case_path / "system").mkdir(exist_ok=True)

        trisurface_dir = case_path / "constant" / "triSurface"
        trisurface_dir.mkdir(parents=True, exist_ok=True)
        dest_stl = trisurface_dir / "geometry.stl"
        shutil.copy(geometry_path, dest_stl)
        shutil.copy(geometry_path, case_path / "geometry.stl")

        self._write_block_mesh_dict(case_path, config)
        self._write_snappy_hex_mesh_dict(case_path, config)
        self._write_control_dict(case_path, config)
        self._write_fv_solution(case_path, config)
        self._write_fv_schemes(case_path, config)
        self._write_transport_properties(case_path, config)
        self._write_turbulence_properties(case_path)
        self._write_initial_fields(case_path, config)

        logger.info(f"Case generated at {case_path}")
        return case_path

    # --------------------------------------------------------

    def _write_block_mesh_dict(self, case_path: Path, config: Dict) -> None:
        content = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}

convertToMeters 1;

vertices
(
    (-5 -5 -5)
    ( 15 -5 -5)
    ( 15  5 -5)
    (-5  5 -5)
    (-5 -5  5)
    ( 15 -5  5)
    ( 15  5  5)
    (-5  5  5)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (40 20 20) simpleGrading (1 1 1)
);

edges
();

boundary
(
    inlet
    {
        type patch;
        faces ((0 3 7 4));
    }
    outlet
    {
        type patch;
        faces ((1 5 6 2));
    }
    walls
    {
        type wall;
        faces
        (
            (0 1 5 4)
            (2 3 7 6)
            (0 4 7 3)
            (1 2 6 5)
        );
    }
);
"""
        (case_path / "system" / "blockMeshDict").write_text(content)

    def _write_snappy_hex_mesh_dict(self, case_path: Path, config: Dict) -> None:
        """Write snappyHexMeshDict for geometry refinement.

        CRITICAL: allowFreeStandingZoneFaces must be TRUE.
        Setting it to false causes the "merge free-standing baffles" crash
        because snappy tries to merge duplicate faces on domain boundaries.
        """
        refinement = config.get("mesh_settings", {}).get("refinement_level", 2)
        snap_level = max(1, min(4, refinement))

        content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      snappyHexMeshDict;
}}

castellatedMesh true;
snap            true;
addLayers       false;

geometry
{{
    geometry.stl
    {{
        type triSurfaceMesh;
        name geometry;
    }}
}}

castellatedMeshControls
{{
    maxLocalCells 500000;
    maxGlobalCells 5000000;
    minRefinementCells 10;
    nCellsBetweenLevels 3;

    features
    (
    );

    refinementSurfaces
    {{
        geometry
        {{
            level ({snap_level} {snap_level + 1});
        }}
    }}

    resolveFeatureAngle 30;

    refinementRegions
    {{
    }}

    locationInMesh (12 0 0);
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}

addLayersControls
{{
    relativeSizes true;
    layers
    {{
    }}
    expansionRatio 1.0;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality 1e-30;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}}

debug 0;
mergeTolerance 1e-6;
"""
        (case_path / "system" / "snappyHexMeshDict").write_text(content)

    def _write_control_dict(self, case_path: Path, config: Dict) -> None:
        solver = config.get("solver_settings", {}).get("solver", "simpleFoam")
        max_iter = config.get("solver_settings", {}).get("max_iterations", 500)
        write_interval = max(1, max_iter // 10)

        content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}}

application     {solver};

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {max_iter};

deltaT          0.5;

writeControl    timeStep;
writeInterval   {write_interval};

purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;

timeFormat      general;
timePrecision   6;

runTimeModifiable true;
"""
        (case_path / "system" / "controlDict").write_text(content)

    def _write_fv_solution(self, case_path: Path, config: Dict) -> None:
        """fvSolution with relaxation factors for laminar stability."""
        tol = config.get("solver_settings", {}).get("convergence_tolerance", 1e-5)

        content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}}

solvers
{{
    p
    {{
        solver          GAMG;
        tolerance       {tol};
        relTol          0.01;
        smoother        GaussSeidel;
    }}

    U
    {{
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       {tol};
        relTol          0.1;
    }}

    Phi
    {{
        solver          GAMG;
        tolerance       {tol};
        relTol          0.0;
        smoother        GaussSeidel;
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors 0;
    consistent      yes;

    pRefCell        0;
    pRefValue       0;
}}

relaxationFactors
{{
    fields
    {{
        p               0.3;
    }}
    equations
    {{
        U               0.5;
    }}
}}
"""
        (case_path / "system" / "fvSolution").write_text(content)

    def _write_fv_schemes(self, case_path: Path, config: Dict) -> None:
        content = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}
"""
        (case_path / "system" / "fvSchemes").write_text(content)

    # --------------------------------------------------------

    def _write_transport_properties(self, case_path: Path, config: Dict) -> None:
        fluid = config.get("fluid", {})
        density = fluid.get("density", 1.225)
        viscosity = fluid.get("dynamic_viscosity", 1.81e-5)
        nu = viscosity / density if density > 0 else 1.5e-5

        content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}}

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {nu:.6e};
"""
        (case_path / "constant" / "transportProperties").write_text(content)

    def _write_turbulence_properties(self, case_path: Path) -> None:
        content = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      turbulenceProperties;
}

simulationType  laminar;
"""
        (case_path / "constant" / "turbulenceProperties").write_text(content)

    # --------------------------------------------------------

    def _write_initial_fields(self, case_path: Path, config: Dict) -> None:
        """LAMINAR: only U and p needed.

        IMPORTANT: For incompressible solvers (simpleFoam), 'p' is
        KINEMATIC pressure (p/rho), not absolute pressure. It must be
        initialized to 0, NOT 101325.
        """
        bc = config.get("boundary_conditions", {})
        inlet = bc.get("inlet", {})

        u_inlet = inlet.get("velocity", 10.0)
        p_outlet = 0.0

        logger.info(
            f"Initial fields (laminar): U={u_inlet} m/s, "
            f"p={p_outlet} (kinematic)"
        )

        u_content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform ({u_inlet} 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({u_inlet} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    walls
    {{
        type            noSlip;
    }}
    "geometry.*"
    {{
        type            noSlip;
    }}
}}
"""
        (case_path / "0" / "U").write_text(u_content)

        p_content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}}

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {p_outlet};

boundaryField
{{
    inlet
    {{
        type            zeroGradient;
    }}
    outlet
    {{
        type            fixedValue;
        value           uniform {p_outlet};
    }}
    walls
    {{
        type            zeroGradient;
    }}
    "geometry.*"
    {{
        type            zeroGradient;
    }}
}}
"""
        (case_path / "0" / "p").write_text(p_content)