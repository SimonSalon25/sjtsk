"""Recognising systems, the bundled grid, control points and the portable implementation."""
from __future__ import annotations

import csv
import hashlib
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

import sjtsk
from sjtsk import control_points as cp
from sjtsk import portable
from slovakia import points

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "control_points" / "example"
DEM_WKT = ('LOCAL_CS["S_JTSK_JTSK03_Krovak_East_North",UNIT["metre",1,AUTHORITY["EPSG","9001"]],'
           'AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","8353"]]')


# ------------------------------------------------------------------ systems and environment

def test_identify():
    from pyproj import CRS
    cases = [("EPSG:5514", sjtsk.JTSK), ("epsg:8353", sjtsk.JTSK03), (4258, sjtsk.ETRS89), ("EPSG:4326", sjtsk.WGS84),
             ("ESRI:102067", sjtsk.JTSK), (CRS("EPSG:8353"), sjtsk.JTSK03), (DEM_WKT, sjtsk.JTSK03),
             (CRS("EPSG:5514").to_wkt(), sjtsk.JTSK), ("EPSG:5513", None), ("EPSG:32634", None), (None, None),
             ("", None), (sjtsk.JTSK03, sjtsk.JTSK03)]
    rasterio = pytest.importorskip("rasterio")
    cases.append((rasterio.crs.CRS.from_epsg(5514), sjtsk.JTSK))
    for value, expected in cases:
        assert sjtsk.identify(value) is expected, value
    assert sjtsk.epsg_from(DEM_WKT) == "8353", "the last AUTHORITY belongs to the system, not to the unit"
    no_code = DEM_WKT.replace(',AUTHORITY["EPSG","8353"]]', ']')     # as a GeoTIFF writes it
    assert sjtsk.epsg_from(no_code) is None
    assert sjtsk.epsg_from(CRS("EPSG:8353").to_wkt("WKT2_2019")) == "8353"
    assert sjtsk.is_unusable(DEM_WKT) and sjtsk.is_unusable(None) and not sjtsk.is_unusable("EPSG:5514")


def test_environment_and_grid():
    ok, message = sjtsk.check_environment()
    assert ok and "grid" in message
    assert sjtsk.grid_path().stat().st_size == 183132
    assert hashlib.sha256(sjtsk.grid_path().read_bytes()).hexdigest() == \
        "e51fea1de2103b80cb843a01b168e4613f9ec0165d4aecbb93c389db6946078e"
    assert (sjtsk.grid_path().parent / "sk_gku_LICENSE.txt").is_file()
    assert sjtsk.DEFAULT_VARIANT == "ugkk" and set(sjtsk.VARIANTS) == {"ugkk", "sk3", "sk4", "proj_auto"}
    with pytest.raises(ValueError, match="ugkk"):
        sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK, "nonexistent")


# ------------------------------------------------------------------ control points

def _copy_modified(modify, slovak=False):
    d = Path(tempfile.mkdtemp())
    with (EXAMPLE / "points.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0])
    rows, fields = modify(rows, fields)
    if slovak:
        back = {v: k for k, v in cp.SLOVAK_COLUMNS.items()}
        fields = [back.get(c, c) for c in fields]
        rows = [{back.get(k, k): v for k, v in r.items()} for r in rows]
    with (d / ("body.csv" if slovak else "points.csv")).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return d


def test_load_example():
    s = cp.load(EXAMPLE)
    assert s.name == "example" and len(s.points) == 12
    p = s.points[0]
    assert p.realization == "JTSK03" and p.en == (-p.y, -p.x) and p.crs is sjtsk.JTSK03
    assert s.metadata.get("publishable") is True
    sk = cp.load(_copy_modified(lambda r, f: (r, f), slovak=True))        # Slovak column names
    assert [q.en for q in sk.points] == [q.en for q in s.points]


def _swap_axes(r, f):
    for x in r:
        x["sjtsk_y"], x["sjtsk_x"] = x["sjtsk_x"], x["sjtsk_y"]
    return r, f


def _negative(r, f):
    for x in r:
        x["sjtsk_y"] = "-" + x["sjtsk_y"]
    return r, f


def _swap_latlon(r, f):
    for x in r:
        x["etrs_lat"], x["etrs_lon"] = x["etrs_lon"], x["etrs_lat"]
    return r, f


def _no_epoch(r, f):
    r[0]["frame"] = "ITRF2020"
    return r, f


def _twice(r, f):
    r[1]["id"] = r[0]["id"]
    return r, f


def _comma(r, f):
    r[0]["etrs_lat"] = r[0]["etrs_lat"].replace(".", ",")
    return r, f


def _no_column(r, f):
    return [{k: v for k, v in x.items() if k != "source"} for x in r], [x for x in f if x != "source"]


@pytest.mark.parametrize("modify,words", [(_swap_axes, "swapped axes"), (_negative, "negative E/N"),
                                          (_swap_latlon, "swapped latitude"), (_no_epoch, "epoch"),
                                          (_twice, "repeated"), (_comma, "decimal point"), (_no_column, "source")])
def test_input_checks(modify, words):
    with pytest.raises(cp.ControlPointError, match=words):
        cp.load(_copy_modified(modify))


def test_evaluation(tmp_path):
    s = cp.load(EXAMPLE)
    results = cp.evaluate(s)
    summary = {r.variant: r.summary() for r in results}
    assert set(summary) == {"ugkk", "sk3", "sk4"} and all(x["points"] == 12 for x in summary.values())
    assert summary["ugkk"]["rmse"] < 0.05 and summary["sk4"]["rmse"] > 0.3
    assert cp.best(results).variant == "ugkk"
    assert "most accurate by RMSE: ugkk" in cp.report(s, results)
    cp.save_csv(results, tmp_path / "residuals.csv")
    assert len((tmp_path / "residuals.csv").read_text(encoding="utf-8").splitlines()) == 1 + 36


# ------------------------------------------------------------------ portable implementation

@pytest.fixture(scope="module")
def grid():
    return portable.Grid.from_file(portable.write_grid(sjtsk.grid_path(), Path(tempfile.mkdtemp()) / "g.lmg"))


def test_portable_grid(grid):
    rasterio = pytest.importorskip("rasterio")
    with rasterio.open(sjtsk.grid_path()) as ds:
        dlat, dlon = ds.read(1), ds.read(2)
        assert (grid.nx, grid.ny) == (ds.width, ds.height)
    for i, j in ((0, 0), (100, 50), (256, 125), (37, 81)):
        assert grid.node(i, j) == (float(np.float32(dlat[j, i])), float(np.float32(dlon[j, i])))
    p = grid.shift(grid.lon0 + 100 * grid.dlon, grid.lat0 - 50 * grid.dlat)
    assert abs(p[0] * 3600 - dlon[50, 100]) < 1e-6 and abs(p[1] * 3600 - dlat[50, 100]) < 1e-6
    assert grid.shift(14.4, 50.1) is None and grid.shift(grid.lon0 - 0.001, 48.0) is None


def test_portable_equals_proj(grid):
    lon, lat = points()
    e, n = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)(lon, lat)
    d = max(math.hypot(a - x, b - y) for a, b, x, y in
            ((*portable.etrs89_to_jtsk(grid, la, lo), x, y) for lo, la, x, y in zip(lon, lat, e, n)))
    assert d < 1e-5, f"forward: {d * 1000:.4f} mm"
    lon2, lat2 = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK).inverse(e, n)
    d = max(max(abs(a - b) for a, b in zip(portable.jtsk_to_etrs89(grid, x, y), (la, lo)))
            for x, y, la, lo in zip(e[::3], n[::3], lat2[::3], lon2[::3]))
    assert d < 1e-10, f"inverse: {d:.2e}°"
    e3, n3 = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK03)(lon, lat)
    dx, dy = sjtsk.jtsk03_to_jtsk_shift(e3, n3)
    d = max(math.hypot(p[0] - a, p[1] - b) for p, a, b in
            ((portable.jtsk03_to_jtsk_shift(grid, x, y), a, b) for x, y, a, b in zip(e3[::4], n3[::4], dx[::4], dy[::4])))
    assert d < 1e-5, f"shift: {d * 1000:.4f} mm"


def test_portable_outside_and_height(grid):
    prague = portable.etrs89_to_jtsk(grid, 50.09, 14.42)
    ref = sjtsk.Converter(sjtsk.ETRS89, sjtsk.JTSK)(14.42, 50.09)
    assert math.hypot(prague[0] - ref[0], prague[1] - ref[1]) < 1e-5
    a, b = portable.etrs89_to_jtsk(grid, 49.17, 20.1, 0.0), portable.etrs89_to_jtsk(grid, 49.17, 20.1, 2600.0)
    assert math.hypot(a[0] - b[0], a[1] - b[1]) < 0.012, "a height of 2,600 m changes the result by less than 12 mm"


def test_export_tool(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "export_portable.py"), str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    assert (tmp_path / "sk_gku_JTSK03_to_JTSK.lmg").stat().st_size == 48 + 257 * 126 * 8
    import json
    ref = json.loads((tmp_path / "reference_points.json").read_text(encoding="utf-8"))
    assert all(len(ref[k]) == 20 for k in ("forward_etrs89_to_5514", "inverse_5514_to_etrs89", "shift_8353_to_5514"))


def test_portable_all_paths(grid):
    """Every pair of 5514 / 8353 / 4258 / 4326 equals the PROJ-based converter."""
    lon, lat = points(0.25, 0.15)
    codes = {5514: sjtsk.JTSK, 8353: sjtsk.JTSK03, 4258: sjtsk.ETRS89, 4326: sjtsk.WGS84}
    for src, s_crs in codes.items():
        x, y = sjtsk.converter(sjtsk.ETRS89, s_crs)(lon, lat)
        for dst, d_crs in codes.items():
            ex, ey = sjtsk.converter(s_crs, d_crs)(x, y)
            got = np.array([portable.transform(grid, src, dst, a, b) for a, b in zip(x, y)])
            geo = dst in (4258, 4326)
            d = np.abs(got[:, 0] - ex).max() + np.abs(got[:, 1] - ey).max()
            assert d < (1e-9 if geo else 1e-5), (src, dst, d)
    with pytest.raises(ValueError, match="supported"):
        portable.transform(grid, 32634, 5514, 0.0, 0.0)
    stats = {}
    portable.transform(grid, 4326, 5514, 14.42, 50.09, stats)       # Prague, outside the grid
    portable.transform(grid, 4326, 5514, 19.0, 48.7, stats)         # inside
    assert stats == {"outside_grid": 1}


def test_portable_grid_from_geotiff(grid):
    pytest.importorskip("osgeo")
    g2 = portable.Grid.from_geotiff(sjtsk.grid_path())
    assert (g2.nx, g2.ny, g2.lon0, g2.lat0, g2.dlon, g2.dlat) == (grid.nx, grid.ny, grid.lon0, grid.lat0, grid.dlon, grid.dlat)
    assert bytes(g2._d) == bytes(grid._d)
