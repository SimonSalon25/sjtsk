"""sjtsk — Slovak S-JTSK (JTSK, JTSK03) ↔ ETRS89 / WGS 84 transformations the official way.

    import sjtsk

    c = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)    # default variant "ugkk" = official ÚGKK chain with the GKÚ grid
    e, n = c(lon, lat)
    lon, lat = c.inverse(e, n)
    sjtsk.transform_gdf(gdf, sjtsk.JTSK)              # instead of gdf.to_crs()
    sjtsk.jtsk03_to_jtsk_shift(e, n)                  # shift of a JTSK03 raster/point to JTSK

The GKÚ grid (CC BY 4.0) is included, so the result does not depend on how PROJ is installed.
"""
from . import control_points, portable
from .crs import ETRS89, JTSK, JTSK03, KNOWN, WGS84, Crs, epsg_from, identify, is_unusable
from .transform import (GRID_PATH, Converter, TransformError, converter, grid_path, jtsk03_to_jtsk_shift,
                        transform_gdf, transform_geometry, transform_points)
from .variants import DEFAULT_VARIANT, VARIANTS, Variant, variant

__version__ = "0.1.0"

__all__ = [
    "JTSK", "JTSK03", "ETRS89", "WGS84", "KNOWN", "Crs", "identify", "epsg_from", "is_unusable",
    "Converter", "converter", "transform_points", "transform_geometry", "transform_gdf", "jtsk03_to_jtsk_shift",
    "TransformError", "grid_path", "GRID_PATH", "VARIANTS", "Variant", "variant", "DEFAULT_VARIANT",
    "control_points", "portable", "check_environment", "__version__",
]


def check_environment() -> tuple[bool, str]:
    """Does the official transformation work in this installation (PROJ, grid)? For start-up checks and logs."""
    try:
        path = grid_path()
        x, y = converter(ETRS89, JTSK)(19.0, 48.7)
        if not (-700000 < x < -150000 and -1400000 < y < -1100000):
            return False, f"the official transformation gave nonsense: {x}, {y}"
        converter(JTSK03, JTSK)(-450000.0, -1250000.0)
        return True, f"official ÚGKK transformation works (grid {path.name})"
    except Exception as exc:  # noqa: BLE001 — the result goes to a log or a message for the user
        return False, f"{type(exc).__name__}: {exc}"
