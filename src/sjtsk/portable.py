"""Portable implementation of the official transformation — pure Python (`math` only, no PROJ) and a simple binary
grid file, as a reference for ports to other languages (the Dart/Flutter mobile application uses the same
algorithm line by line).

Why: the full PROJ is not available everywhere (mobile apps, browsers, microcontrollers). This module does exactly
what the PROJ chain does; the tests compare it with `sjtsk.converter` (= PROJ with the GKÚ grid) on 3,978 points
covering Slovakia (agreement better than 0.01 mm). A port to another language can be checked the same way against
the reference points written by `tools/export_portable.py`.

Grid file format `LMGRID01` (little-endian):
    0   8 B  magic b"LMGRID01"
    8   4×f8 lon0, lat0 (degrees; node [0,0] = WEST, NORTH), dlon, dlat (degrees, positive)
    40  2×i4 nx (columns, eastwards), ny (rows, southwards)
    48  nx·ny × 2×f4 shifts in arc seconds, row by row from the north: (dlat, dlon), dlon positive EAST
Values are grid nodes (pixel centres of the GeoTIFF); bilinear in between, as PROJ `hgridshift`.
"""
from __future__ import annotations

import math
import struct
from pathlib import Path

MAGIC = b"LMGRID01"


# ------------------------------------------------------------------ grid

def write_grid(tif, target) -> Path:
    """GKÚ grid GeoTIFF → portable binary file. Needs rasterio."""
    import numpy as np
    import rasterio
    with rasterio.open(tif) as ds:
        dlat, dlon = ds.read(1).astype("<f4"), ds.read(2).astype("<f4")
        t = ds.transform
        bands = ds.descriptions
    if tuple(bands) != ("latitude_offset", "longitude_offset"):
        raise ValueError(f"unexpected grid bands: {bands}")
    ny, nx = dlat.shape
    lon0, lat0 = t.c + t.a / 2, t.f + t.e / 2            # centre of the top-left pixel = node [0,0]
    header = MAGIC + struct.pack("<4d2i", lon0, lat0, t.a, -t.e, nx, ny)
    data = np.empty((ny, nx, 2), dtype="<f4")
    data[..., 0], data[..., 1] = dlat, dlon
    target = Path(target)
    target.write_bytes(header + data.tobytes())
    return target


class Grid:
    def __init__(self, data: bytes):
        if data[:8] != MAGIC:
            raise ValueError("not an LMGRID01 grid")
        self.lon0, self.lat0, self.dlon, self.dlat, self.nx, self.ny = struct.unpack_from("<4d2i", data, 8)
        self._d = memoryview(data)[48:].cast("f")

    @classmethod
    def from_file(cls, path):
        return cls(Path(path).read_bytes())

    @classmethod
    def from_geotiff(cls, path):
        """Build the grid directly from the GKÚ GeoTIFF with GDAL (`osgeo`, e.g. inside QGIS) — no extra file."""
        from osgeo import gdal
        ds = gdal.Open(str(path))
        if ds is None:
            raise ValueError(f"cannot open {path}")
        try:
            bands = tuple(ds.GetRasterBand(i).GetDescription() for i in (1, 2))
            if bands != ("latitude_offset", "longitude_offset"):
                raise ValueError(f"unexpected grid bands: {bands}")
            nx, ny = ds.RasterXSize, ds.RasterYSize
            x0, dx, _r1, y0, _r2, dy = ds.GetGeoTransform()
            dlat = ds.GetRasterBand(1).ReadRaster(0, 0, nx, ny, buf_type=gdal.GDT_Float32)
            dlon = ds.GetRasterBand(2).ReadRaster(0, 0, nx, ny, buf_type=gdal.GDT_Float32)
        finally:
            ds = None
        a = struct.unpack(f"<{nx * ny}f", dlat)
        b = struct.unpack(f"<{nx * ny}f", dlon)
        inter = [v for pair in zip(a, b) for v in pair]
        header = MAGIC + struct.pack("<4d2i", x0 + dx / 2, y0 + dy / 2, dx, -dy, nx, ny)
        return cls(header + struct.pack(f"<{2 * nx * ny}f", *inter))

    def node(self, i, j):
        k = 2 * (j * self.nx + i)
        return self._d[k], self._d[k + 1]

    def shift(self, lon, lat):
        """(dlon, dlat) in degrees at a point (degrees); None outside the grid."""
        fx = (lon - self.lon0) / self.dlon
        fy = (self.lat0 - lat) / self.dlat
        i, j = math.floor(fx), math.floor(fy)
        if i < 0 or j < 0 or i >= self.nx - 1 or j >= self.ny - 1:
            return None
        tx, ty = fx - i, fy - j
        a, b, c, d = self.node(i, j), self.node(i + 1, j), self.node(i, j + 1), self.node(i + 1, j + 1)
        dlat = (a[0] * (1 - tx) + b[0] * tx) * (1 - ty) + (c[0] * (1 - tx) + d[0] * tx) * ty
        dlon = (a[1] * (1 - tx) + b[1] * tx) * (1 - ty) + (c[1] * (1 - tx) + d[1] * tx) * ty
        return dlon / 3600.0, dlat / 3600.0


# ------------------------------------------------------------------ ellipsoids, Helmert, Křovák

GRS80 = (6378137.0, 1 / 298.257222101)
BESSEL = (6377397.155, 1 / 299.1528128)
# EPSG:8365 ETRS89 → JTSK03 and EPSG:8367 JTSK03 → ETRS89 (coordinate frame), as in variants.py
H_ETRS_J03 = (-485.014055, -169.473618, -483.842943, 7.78625453, 4.39770887, 4.10248899, 0.0)
H_J03_ETRS = (485.021, 169.465, 483.839, -7.786342, -4.397554, -4.102655, 0.0)


def geo_to_xyz(lat, lon, h, ellps):
    a, f = ellps
    e2 = f * (2 - f)
    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    return ((n + h) * math.cos(lat) * math.cos(lon), (n + h) * math.cos(lat) * math.sin(lon),
            (n * (1 - e2) + h) * math.sin(lat))


def xyz_to_geo(x, y, z, ellps):
    a, f = ellps
    e2 = f * (2 - f)
    p = math.hypot(x, y)
    lon = math.atan2(y, x)
    lat = math.atan2(z, p * (1 - e2))
    h = 0.0
    for _ in range(10):
        n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        h = p / math.cos(lat) - n
        lat = math.atan2(z, p * (1 - e2 * n / (n + h)))
    return lat, lon, h


def helmert_cf(x, y, z, par):
    """Coordinate frame (EPSG 1032): X' = T + (1+s)·R·X, R = [[1, rz, −ry], [−rz, 1, rx], [ry, −rx, 1]]."""
    tx, ty, tz, rx, ry, rz, s = par
    k = math.pi / 180 / 3600
    rx, ry, rz, m = rx * k, ry * k, rz * k, 1 + s * 1e-6
    return (tx + m * (x + rz * y - ry * z),
            ty + m * (-rz * x + y + rx * z),
            tz + m * (ry * x - rx * y + z))


# Křovák (EPSG method 9819), S-JTSK, Greenwich
_FI0, _LAM0 = math.radians(49.5), math.radians(24.8333333333333)
_ALFA, _FIP, _KP = math.radians(30.2881397527778), math.radians(78.5), 0.9999


def _krovak_constants():
    a, f = BESSEL
    e2 = f * (2 - f)
    e = math.sqrt(e2)
    b = math.sqrt(1 + e2 * math.cos(_FI0) ** 4 / (1 - e2))
    aa = a * math.sqrt(1 - e2) / (1 - e2 * math.sin(_FI0) ** 2)
    g0 = math.asin(math.sin(_FI0) / b)
    t0 = (math.tan(math.pi / 4 + g0 / 2) * ((1 + e * math.sin(_FI0)) / (1 - e * math.sin(_FI0))) ** (e * b / 2)
          / math.tan(math.pi / 4 + _FI0 / 2) ** b)
    n = math.sin(_FIP)
    r0 = _KP * aa / math.tan(_FIP)
    return e, b, t0, n, r0


def krovak(lat, lon):
    """Bessel (rad) → EPSG:5514 / 8353 (E, N)."""
    e, b, t0, n, r0 = _krovak_constants()
    u = 2 * (math.atan(t0 * math.tan(lat / 2 + math.pi / 4) ** b
                       / ((1 + e * math.sin(lat)) / (1 - e * math.sin(lat))) ** (e * b / 2)) - math.pi / 4)
    v = b * (_LAM0 - lon)
    t = math.asin(math.cos(_ALFA) * math.sin(u) + math.sin(_ALFA) * math.cos(u) * math.cos(v))
    d = math.asin(math.cos(u) * math.sin(v) / math.cos(t))
    theta = n * d
    r = r0 * math.tan(math.pi / 4 + _FIP / 2) ** n / math.tan(t / 2 + math.pi / 4) ** n
    return -r * math.sin(theta), -r * math.cos(theta)


def krovak_inverse(e_, n_):
    """EPSG:5514 / 8353 (E, N) → Bessel (rad)."""
    e, b, t0, n, r0 = _krovak_constants()
    xp, yp = -n_, -e_                                     # south, west
    r = math.hypot(xp, yp)
    theta = math.atan2(yp, xp)
    d = theta / n
    t = 2 * (math.atan((r0 / r) ** (1 / n) * math.tan(math.pi / 4 + _FIP / 2)) - math.pi / 4)
    u = math.asin(math.cos(_ALFA) * math.sin(t) - math.sin(_ALFA) * math.cos(t) * math.cos(d))
    v = math.asin(math.cos(t) * math.sin(d) / math.cos(u))
    lon = _LAM0 - v / b
    lat = u
    for _ in range(15):
        lat = 2 * (math.atan(t0 ** (-1 / b) * math.tan(u / 2 + math.pi / 4) ** (1 / b)
                             * ((1 + e * math.sin(lat)) / (1 - e * math.sin(lat))) ** (e / 2)) - math.pi / 4)
    return lat, lon


# ------------------------------------------------------------------ full paths

def _outside(stats):
    if stats is not None:
        stats["outside_grid"] = stats.get("outside_grid", 0) + 1


def _grid_forward(g: Grid, lat, lon, stats=None):
    """JTSK03 → JTSK on Bessel (rad); outside the grid no shift (as the PROJ-based converter), counted in stats."""
    p = g.shift(math.degrees(lon), math.degrees(lat))
    if p is None:
        _outside(stats)
        return lat, lon, False
    return lat + math.radians(p[1]), lon + math.radians(p[0]), True


def _grid_inverse(g: Grid, lat, lon, stats=None):
    """JTSK → JTSK03 by iteration (as PROJ for the inverse hgridshift)."""
    la, lo = lat, lon
    for _ in range(10):
        p = g.shift(math.degrees(lo), math.degrees(la))
        if p is None:
            _outside(stats)
            return lat, lon, False
        nla, nlo = lat - math.radians(p[1]), lon - math.radians(p[0])
        if abs(nla - la) < 1e-14 and abs(nlo - lo) < 1e-14:
            la, lo = nla, nlo
            break
        la, lo = nla, nlo
    return la, lo, True


def etrs89_to_jtsk(g: Grid, lat_deg, lon_deg, h=0.0, stats=None):
    """ETRS89/WGS 84 (degrees) → EPSG:5514 (E, N), official chain. `h` = ellipsoidal height (PROJ path uses 0)."""
    x, y, z = geo_to_xyz(math.radians(lat_deg), math.radians(lon_deg), h, GRS80)
    x, y, z = helmert_cf(x, y, z, H_ETRS_J03)
    lat, lon, _h = xyz_to_geo(x, y, z, BESSEL)
    lat, lon, _ok = _grid_forward(g, lat, lon, stats)
    return krovak(lat, lon)


def jtsk_to_etrs89(g: Grid, e, n, stats=None):
    """EPSG:5514 (E, N) → ETRS89 (lat, lon in degrees), official reverse direction (EPSG 8367)."""
    lat, lon = krovak_inverse(e, n)
    lat, lon, _ok = _grid_inverse(g, lat, lon, stats)
    x, y, z = geo_to_xyz(lat, lon, 0.0, BESSEL)
    x, y, z = helmert_cf(x, y, z, H_J03_ETRS)
    lat, lon, _h = xyz_to_geo(x, y, z, GRS80)
    return math.degrees(lat), math.degrees(lon)


def etrs89_to_jtsk03(lat_deg, lon_deg, h=0.0):
    """ETRS89/WGS 84 (degrees) → EPSG:8353 (E, N) — ÚGKK Helmert only, no grid needed."""
    x, y, z = geo_to_xyz(math.radians(lat_deg), math.radians(lon_deg), h, GRS80)
    lat, lon, _h = xyz_to_geo(*helmert_cf(x, y, z, H_ETRS_J03), BESSEL)
    return krovak(lat, lon)


def jtsk03_to_etrs89(e, n):
    """EPSG:8353 (E, N) → ETRS89 (lat, lon in degrees) — ÚGKK reverse Helmert (EPSG 8367)."""
    lat, lon = krovak_inverse(e, n)
    x, y, z = geo_to_xyz(lat, lon, 0.0, BESSEL)
    lat, lon, _h = xyz_to_geo(*helmert_cf(x, y, z, H_J03_ETRS), GRS80)
    return math.degrees(lat), math.degrees(lon)


def jtsk03_to_jtsk(g: Grid, e, n, stats=None):
    """EPSG:8353 → EPSG:5514 by the grid."""
    lat, lon = krovak_inverse(e, n)
    lat, lon, _ok = _grid_forward(g, lat, lon, stats)
    return krovak(lat, lon)


def jtsk_to_jtsk03(g: Grid, e, n, stats=None):
    """EPSG:5514 → EPSG:8353 by the grid (inverse by iteration)."""
    lat, lon = krovak_inverse(e, n)
    lat, lon, _ok = _grid_inverse(g, lat, lon, stats)
    return krovak(lat, lon)


#: EPSG codes handled by `transform`; 4326 (WGS 84) is taken as ETRS89, 102067 is EPSG:5514
SUPPORTED = {5514: "jtsk", 102067: "jtsk", 8353: "j03", 4258: "etrs", 4326: "etrs"}


def transform(g: Grid, src: int, dst: int, x: float, y: float, stats: dict | None = None) -> tuple[float, float]:
    """One point between EPSG 5514 / 8353 / 4258 / 4326, official chain. Geographic input/output is (lon, lat).

    Points outside the grid (outside Slovakia) get the Helmert only and are counted in `stats["outside_grid"]`.
    """
    a, b = SUPPORTED.get(int(src)), SUPPORTED.get(int(dst))
    if a is None or b is None:
        raise ValueError(f"only EPSG {sorted(SUPPORTED)} are supported, not {src} → {dst}")
    if a == b:
        return x, y
    if a == "etrs":
        lat, lon = y, x
        if b == "jtsk":
            return etrs89_to_jtsk(g, lat, lon, stats=stats)
        return etrs89_to_jtsk03(lat, lon)
    if b == "etrs":
        lat, lon = jtsk_to_etrs89(g, x, y, stats) if a == "jtsk" else jtsk03_to_etrs89(x, y)
        return lon, lat
    return jtsk03_to_jtsk(g, x, y, stats) if a == "j03" else jtsk_to_jtsk03(g, x, y, stats)


def jtsk03_to_jtsk_shift(g: Grid, e, n):
    """(dx, dy): a point in 8353 + shift = the point in 5514 (plane)."""
    lat, lon = krovak_inverse(e, n)
    lat, lon, _ok = _grid_forward(g, lat, lon)
    e2, n2 = krovak(lat, lon)
    return e2 - e, n2 - n
