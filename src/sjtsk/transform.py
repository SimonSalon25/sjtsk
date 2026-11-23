"""Coordinate transformation with an EXPLICIT variant.

Paths (nodes):  JTSK plane (5514)   ─ Bessel JTSK ───┐
                JTSK03 plane (8353) ─ Bessel JTSK03 ─┼─ ETRS89 (4258; WGS 84 taken as ETRS89)
                any other system ─ PROJ ─ ETRS89 ────┘

* Between JTSK and JTSK03 always the GKÚ grid (EPSG:8364) — directly, never through ETRS89.
* Between JTSK03 and ETRS89 always the ÚGKK Helmert (8365 / 8367, accuracy 1 mm).
* Between JTSK and ETRS89 by variant: `ugkk` = through JTSK03 (Helmert + grid), `sk3`, `sk4`.
* WGS 84 is taken as ETRS89 (zero shift). Today they differ by ~1.0 m (ITRF2020 at epoch 2026.9 versus ETRF2000);
  irrelevant for phone GNSS (3–5 m). Who needs more converts WGS 84 to ETRS89 with the epoch and passes ETRS89.
* A point outside the grid (outside Slovakia) gets only the Helmert (JTSK03 taken as JTSK) and the transformer
  counts it in `outside_grid` — never a silent switch to another result.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer
from pyproj.enums import TransformDirection

from . import crs as _c
from . import variants as _v

logger = logging.getLogger(__name__)

GRID_PATH = Path(__file__).resolve().parent / "data" / _v.GRID


class TransformError(RuntimeError):
    """The transformation cannot be done (unusable CRS, missing grid)."""


# ---------------------------------------------------------------- building blocks

def _helmert_pipeline(param: dict, from_ellps: str, to_ellps: str, operation: str = "helmert") -> str:
    p = " ".join(f"+{k}={v}" for k, v in param.items())
    return ("+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=push +v_3 "
            f"+step +proj=cart +ellps={from_ellps} +step +proj={operation} {p} "
            f"+step +inv +proj=cart +ellps={to_ellps} +step +proj=pop +v_3 "
            "+step +proj=unitconvert +xy_in=rad +xy_out=deg")


@lru_cache(maxsize=None)
def _t_pipeline(pipeline: str) -> Transformer:
    return Transformer.from_pipeline(pipeline)


@lru_cache(maxsize=None)
def _t_crs(src: str, dst: str) -> Transformer:
    return Transformer.from_crs(src, dst, always_xy=True)


def grid_path() -> Path:
    if not GRID_PATH.is_file():
        raise TransformError(f"the GKÚ grid {GRID_PATH} is missing — incomplete installation")
    return GRID_PATH


def _grid_pipeline() -> str:
    # Absolute path in quotes — independent of PROJ_DATA and of other GIS installations; PROJ accepts it
    # with spaces and with forward slashes on Windows.
    return ("+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad "
            f'+step +proj=hgridshift +grids="{grid_path().as_posix()}" '
            "+step +proj=unitconvert +xy_in=rad +xy_out=deg")


def _arr(a):
    return np.array(a, dtype=np.float64, ndmin=1, copy=True)


class _Steps:
    """Steps between nodes, on numpy arrays (lon/lat in degrees, plane in metres)."""

    def __init__(self):
        self.outside_grid = 0

    # planes ↔ Bessel (projection only, no datum change)
    @staticmethod
    def jtsk_plane_to_geo(x, y):
        return _t_crs("EPSG:5514", "EPSG:4156").transform(x, y)

    @staticmethod
    def jtsk_geo_to_plane(lo, la):
        return _t_crs("EPSG:4156", "EPSG:5514").transform(lo, la)

    @staticmethod
    def j03_plane_to_geo(x, y):
        return _t_crs("EPSG:8353", "EPSG:8351").transform(x, y)

    @staticmethod
    def j03_geo_to_plane(lo, la):
        return _t_crs("EPSG:8351", "EPSG:8353").transform(lo, la)

    # grid JTSK03 ↔ JTSK (on the Bessel ellipsoid)
    def _grid(self, lo, la, direction):
        a, b = _t_pipeline(_grid_pipeline()).transform(lo, la, direction=direction)
        a, b = _arr(a), _arr(b)
        bad = ~(np.isfinite(a) & np.isfinite(b))
        if bad.any():
            n = int(bad.sum())
            self.outside_grid += n
            (logger.warning if self.outside_grid == n else logger.debug)(
                "sjtsk: %d point(s) outside the GKÚ grid (outside Slovakia) — Helmert only, without the "
                "JTSK03↔JTSK correction (error up to ~1.6 m)", n)
            a[bad] = _arr(lo)[bad]
            b[bad] = _arr(la)[bad]
        return a, b

    def j03_geo_to_jtsk_geo(self, lo, la):
        return self._grid(lo, la, TransformDirection.FORWARD)

    def jtsk_geo_to_j03_geo(self, lo, la):
        return self._grid(lo, la, TransformDirection.INVERSE)

    # ETRS89 ↔ JTSK03 (ÚGKK)
    @staticmethod
    def etrs_to_j03_geo(lo, la):
        return _t_pipeline(_helmert_pipeline(_v.HELMERT_ETRS89_TO_JTSK03, "GRS80", "bessel")).transform(lo, la)

    @staticmethod
    def j03_geo_to_etrs(lo, la):
        return _t_pipeline(_helmert_pipeline(_v.HELMERT_JTSK03_TO_ETRS89, "bessel", "GRS80")).transform(lo, la)

    # ETRS89 ↔ JTSK by variant
    def jtsk_geo_to_etrs(self, lo, la, variant):
        if variant == "ugkk":
            return self.j03_geo_to_etrs(*self.jtsk_geo_to_j03_geo(lo, la))
        return self._static(variant).transform(lo, la)

    def etrs_to_jtsk_geo(self, lo, la, variant):
        if variant == "ugkk":
            return self.j03_geo_to_jtsk_geo(*self.etrs_to_j03_geo(lo, la))
        return self._static(variant).transform(lo, la, direction=TransformDirection.INVERSE)

    @staticmethod
    def _static(variant):
        if variant == "sk4":
            return _t_pipeline(_helmert_pipeline(_v.HELMERT_SK4, "bessel", "GRS80"))
        if variant == "sk3":
            return _t_pipeline(_helmert_pipeline(_v.MB_SK3, "bessel", "GRS80", "molobadekas"))
        raise ValueError(variant)


# ---------------------------------------------------------------- nodes

#: plane of a node into which other notations of the same datum are converted (projection change only)
_NODE_PLANE = {"jtsk": "EPSG:5514", "j03": "EPSG:8353"}


def _sjtsk_datum(crs) -> str | None:
    """'jtsk' / 'j03' when the system is on the S-JTSK datum in the JTSK or JTSK03 realization, else None.

    EPSG:5513 (S-JTSK / Krovak with positive south/west axes — the axes of Slovak cadastral deliveries),
    EPSG:2065 (Ferro), EPSG:8352 … are the same realization as a node, only with other axes or prime meridian;
    they are converted without any datum shift. The Czech S-JTSK/05 is another realization ("other system").
    """
    try:
        name = crs.geodetic_crs.datum.name
    except Exception:  # noqa: BLE001
        return None
    if "Unified Trigonometrical Cadastral Network" not in name or "/05" in name:
        return None
    return "j03" if "JTSK03" in name else "jtsk"


def _node(system) -> tuple[str, object]:
    """('jtsk' | 'j03' | 'etrs' | 'other', CRS). For 'jtsk'/'j03' the CRS is another notation of the same
    datum (converted to the node plane), for 'other' a system transformed through ETRS89."""
    s = _c.identify(system)
    if s is _c.JTSK:
        return "jtsk", None
    if s is _c.JTSK03:
        return "j03", None
    if s in (_c.ETRS89, _c.WGS84):
        return "etrs", None
    if _c.is_unusable(system):
        raise TransformError(f"the coordinate reference system cannot be used for a transformation "
                             f"(empty or LOCAL_CS): {system!r}")
    to_wkt = getattr(system, "to_wkt", None)
    crs = CRS.from_user_input(to_wkt() if callable(to_wkt) else system)
    node = _sjtsk_datum(crs)
    if node is not None:
        return node, crs
    return "other", crs


class Converter:
    """Transformation from one system to another: `c(x, y)`, back `c.inverse(x, y)`.

    Input and output in (east, north) resp. (longitude, latitude) order. A scalar gives a scalar, an array an array.
    """

    def __init__(self, src, dst, variant: str = _v.DEFAULT_VARIANT):
        self.variant = _v.variant(variant)
        self.src, self.dst = src, dst
        self._ns, self._crs_s = _node(src)
        self._nd, self._crs_d = _node(dst)
        self._k = _Steps()

    @property
    def outside_grid(self) -> int:
        """How many points since creation went outside the grid (Helmert only)."""
        return self._k.outside_grid

    @property
    def description(self) -> str:
        return f"{self.src} → {self.dst}, variant {self.variant.name}: {self.variant.description}"

    def __call__(self, x, y):
        return self._run(x, y, self._ns, self._crs_s, self._nd, self._crs_d)

    def inverse(self, x, y):
        return self._run(x, y, self._nd, self._crs_d, self._ns, self._crs_s)

    def _run(self, x, y, ns, crs_s, nd, crs_d):
        scalar = np.ndim(x) == 0 and np.ndim(y) == 0
        x, y = _arr(x), _arr(y)
        if self.variant.name == "proj_auto":
            a, b = _t_crs(_crs_text(ns, crs_s), _crs_text(nd, crs_d)).transform(x, y)
        else:
            a, b = self._path(x, y, ns, crs_s, nd, crs_d)
        a, b = _arr(a), _arr(b)
        if scalar:
            return float(a[0]), float(b[0])
        return a, b

    def _path(self, x, y, ns, crs_s, nd, crs_d):
        # another notation of the S-JTSK datum (5513, 2065, 8352 …) → node plane, projection change only
        if ns in _NODE_PLANE and crs_s is not None:
            x, y = _t_crs(crs_s.to_wkt(), _NODE_PLANE[ns]).transform(x, y)
            crs_s = None
        if nd in _NODE_PLANE and crs_d is not None:
            a, b = self._path(x, y, ns, crs_s, nd, None)
            return _t_crs(_NODE_PLANE[nd], crs_d.to_wkt()).transform(a, b)
        k, v = self._k, self.variant.name
        if ns == nd and ns != "other":
            return x, y
        if ns == "other" and nd == "other":
            return _t_crs(crs_s.to_wkt(), crs_d.to_wkt()).transform(x, y)
        # JTSK ↔ JTSK03 directly — grid, no detour through ETRS89
        if ns == "j03" and nd == "jtsk":
            return k.jtsk_geo_to_plane(*k.j03_geo_to_jtsk_geo(*k.j03_plane_to_geo(x, y)))
        if ns == "jtsk" and nd == "j03":
            return k.j03_geo_to_plane(*k.jtsk_geo_to_j03_geo(*k.jtsk_plane_to_geo(x, y)))
        # to ETRS89
        if ns == "jtsk":
            lo, la = k.jtsk_geo_to_etrs(*k.jtsk_plane_to_geo(x, y), v)
        elif ns == "j03":
            lo, la = k.j03_geo_to_etrs(*k.j03_plane_to_geo(x, y))
        elif ns == "etrs":
            lo, la = x, y
        else:
            lo, la = _t_crs(crs_s.to_wkt(), "EPSG:4258").transform(x, y)
        # from ETRS89
        if nd == "jtsk":
            return k.jtsk_geo_to_plane(*k.etrs_to_jtsk_geo(lo, la, v))
        if nd == "j03":
            return k.j03_geo_to_plane(*k.etrs_to_j03_geo(lo, la))
        if nd == "etrs":
            return lo, la
        return _t_crs("EPSG:4258", crs_d.to_wkt()).transform(lo, la)


def _crs_text(node, crs):
    return {"jtsk": "EPSG:5514", "j03": "EPSG:8353", "etrs": "EPSG:4258"}.get(node) or crs.to_wkt()


@lru_cache(maxsize=64)
def _cached(src, dst, variant):
    return Converter(src, dst, variant)


def converter(src, dst, variant: str = _v.DEFAULT_VARIANT) -> Converter:
    """Converter from `src` to `dst` (Crs, "EPSG:n", a number, WKT, pyproj/rasterio CRS)."""
    try:
        return _cached(src, dst, variant)
    except TypeError:            # unhashable input (some CRS objects)
        return Converter(src, dst, variant)


def transform_points(x, y, src, dst, variant: str = _v.DEFAULT_VARIANT):
    return converter(src, dst, variant)(x, y)


def transform_geometry(geometry, src, dst, variant: str = _v.DEFAULT_VARIANT):
    """A shapely geometry (or array of geometries) with every vertex transformed."""
    import shapely

    c = converter(src, dst, variant)

    def _f(coords):
        if len(coords) == 0:
            return coords
        a, b = c(coords[:, 0], coords[:, 1])
        return np.column_stack([a, b])

    return shapely.transform(geometry, _f)


def transform_gdf(gdf, dst, variant: str = _v.DEFAULT_VARIANT, src=None):
    """GeoDataFrame to `dst` — a replacement for `gdf.to_crs()` with a known variant.

    `src` = the input system if `gdf.crs` has none (otherwise `gdf.crs` is used).
    """
    source = src if src is not None else gdf.crs
    if source is None:
        raise TransformError("the layer has no coordinate reference system — cannot transform")
    target = _c.identify(dst)
    target_text = target.epsg_text if target else CRS.from_user_input(dst).to_wkt()
    out = gdf.copy()
    if target is not None and _c.identify(source) is target:      # same system (e.g. ESRI:102067 = 5514)
        return out.set_crs(target_text, allow_override=True)
    import geopandas as gpd

    new = transform_geometry(np.asarray(gdf.geometry.values), source, dst, variant)
    column = gdf.geometry.name
    out[column] = gpd.GeoSeries(new, index=gdf.index, crs=target_text)
    return out.set_geometry(column).set_crs(target_text, allow_override=True)


def jtsk03_to_jtsk_shift(x, y):
    """Shift (dx, dy) in the Křovák plane: a JTSK03 point (8353) + shift = the same point in JTSK (5514)."""
    a, b = converter(_c.JTSK03, _c.JTSK)(x, y)
    if np.ndim(a) == 0:
        return a - float(x), b - float(y)
    return a - _arr(x), b - _arr(y)
