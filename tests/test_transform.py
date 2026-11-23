"""Transformation: agreement with PROJ, the published numbers, behaviour at the edges."""
from __future__ import annotations

import shutil
import tempfile

import numpy as np
import pytest

import sjtsk
from slovakia import points


def _proj_with_grid():
    """PROJ that knows the GKÚ grid (as if installed) — the reference for ugkk."""
    import pyproj
    d = tempfile.mkdtemp()
    shutil.copy(sjtsk.grid_path(), d)
    pyproj.datadir.append_data_dir(d)
    return pyproj


def test_ugkk_equals_proj_with_grid():
    pyproj = _proj_with_grid()
    lon, lat = points()
    ref = pyproj.Transformer.from_crs("EPSG:4258", "EPSG:5514", always_xy=True).transform(lon, lat)
    mine = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)(lon, lat)
    assert np.hypot(ref[0] - mine[0], ref[1] - mine[1]).max() < 1e-5, "ugkk ≠ EPSG 'ETRS89 to S-JTSK (5)'"
    ref = pyproj.Transformer.from_crs("EPSG:5514", "EPSG:4258", always_xy=True).transform(*mine)
    back = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK).inverse(*mine)
    assert np.hypot(ref[0] - back[0], ref[1] - back[1]).max() < 1e-9, "inverse ≠ EPSG 'S-JTSK to ETRS89 (6)'"
    e3, n3 = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK03)(lon, lat)
    ref = pyproj.Transformer.from_crs("EPSG:8353", "EPSG:5514", always_xy=True).transform(e3, n3)
    mine = sjtsk.converter(sjtsk.JTSK03, sjtsk.JTSK)(e3, n3)
    assert np.hypot(ref[0] - mine[0], ref[1] - mine[1]).max() < 1e-5, "JTSK03 → JTSK ≠ grid EPSG:8364"


def test_variants_are_the_epsg_operations():
    import pyproj
    from pyproj.transformer import TransformerGroup
    lon, lat = points(0.2, 0.1)
    for name, title in (("sk3", "S-JTSK to ETRS89 (3)"), ("sk4", "S-JTSK to ETRS89 (4)")):
        t = [t for t in TransformerGroup("EPSG:4258", "EPSG:5514", always_xy=True).transformers
             if title in t.description][0]
        ref = t.transform(lon, lat)
        mine = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK, name)(lon, lat)
        assert np.hypot(ref[0] - mine[0], ref[1] - mine[1]).max() < 1e-5, name
    auto = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK, "proj_auto")(lon, lat)
    ref = pyproj.Transformer.from_crs("EPSG:4258", "EPSG:5514", always_xy=True).transform(lon, lat)
    assert np.allclose(auto, ref)


def test_published_numbers():
    """The table in METHODOLOGY.md, section 3 — these numbers go into the paper."""
    lon, lat = points()
    assert lon.size == 3978
    ref = np.array(sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)(lon, lat))
    for name, (mean, maximum) in {"sk3": (0.310, 1.120), "sk4": (0.681, 1.692)}.items():
        d = np.hypot(*(np.array(sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK, name)(lon, lat)) - ref))
        assert abs(d.mean() - mean) < 0.002 and abs(d.max() - maximum) < 0.002, (name, d.mean(), d.max())
    e3, n3 = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK03)(lon, lat)
    d = np.hypot(e3 - ref[0], n3 - ref[1])
    assert abs(d.mean() - 0.687) < 0.002 and abs(d.max() - 1.637) < 0.002


def test_wgs84_one_path():
    lon, lat = points(0.2, 0.1)
    a = sjtsk.converter(sjtsk.WGS84, sjtsk.JTSK)(lon, lat)
    b = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)(lon, lat)
    assert np.array_equal(a, b)
    assert np.array_equal(sjtsk.converter("EPSG:4326", "EPSG:5514")(lon, lat), b)


def test_input_forms_and_systems():
    x, y = sjtsk.converter(sjtsk.JTSK, sjtsk.ETRS89)(-480000.0, -1170000.0)
    assert isinstance(x, float) and 18 < x < 20 and 48 < y < 50
    a, _b = sjtsk.converter(sjtsk.JTSK, sjtsk.ETRS89)([-480000.0], [-1170000.0])
    assert isinstance(a, np.ndarray) and a[0] == x
    c = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)
    lon2, lat2 = c.inverse(*c(19.1, 48.7))
    assert abs(lon2 - 19.1) < 2e-7 and abs(lat2 - 48.7) < 2e-7
    e, n = sjtsk.converter("EPSG:32634", sjtsk.JTSK)(350000.0, 5400000.0)
    assert -700000 < e < -150000 and -1400000 < n < -1100000
    assert sjtsk.converter("ESRI:102067", sjtsk.JTSK)(-450000.0, -1250000.0) == (-450000.0, -1250000.0)
    with pytest.raises(sjtsk.TransformError):
        sjtsk.converter('LOCAL_CS["x",AUTHORITY["EPSG","9999"]]', sjtsk.JTSK)
    wkt = 'LOCAL_CS["S_JTSK_JTSK03_Krovak_East_North",UNIT["metre",1],AUTHORITY["EPSG","8353"]]'
    assert sjtsk.identify(wkt) is sjtsk.JTSK03


def test_jtsk03_and_outside_grid():
    e, n = -580000.0, -1280000.0                     # near Bratislava, the largest difference
    dx, dy = sjtsk.jtsk03_to_jtsk_shift(e, n)
    assert 1.4 < np.hypot(dx, dy) < 1.7
    back = sjtsk.converter(sjtsk.JTSK03, sjtsk.JTSK).inverse(e + dx, n + dy)
    assert np.hypot(back[0] - e, back[1] - n) < 1e-4
    c = sjtsk.Converter(sjtsk.ETRS89, sjtsk.JTSK)    # own instance so the counter starts at 0
    outside = c(14.42, 50.09)                        # Prague — outside the grid
    assert c.outside_grid == 1
    helmert = sjtsk.converter(sjtsk.JTSK03, sjtsk.JTSK).inverse(*outside)
    assert np.all(np.isfinite(outside)) and np.hypot(helmert[0] - outside[0], helmert[1] - outside[1]) < 1e-6


def test_geometries_and_gdf():
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Point, Polygon
    poly = Polygon([(19.0, 48.7), (19.01, 48.7), (19.01, 48.71), (19.0, 48.71)])
    gdf = gpd.GeoDataFrame({"id": ["a", "b"], "geom": [poly, Point(19.1, 48.6)]}, geometry="geom", crs="EPSG:4326")
    out = sjtsk.transform_gdf(gdf, sjtsk.JTSK)
    assert list(out.columns) == ["id", "geom"] and out.geometry.name == "geom" and out.crs.to_epsg() == 5514
    expected = sjtsk.converter(sjtsk.WGS84, sjtsk.JTSK)(19.1, 48.6)
    assert abs(out.geometry.iloc[1].x - expected[0]) < 1e-9 and abs(out.geometry.iloc[1].y - expected[1]) < 1e-9
    assert gdf.crs.to_epsg() == 4326 and gdf.geometry.iloc[1].x == 19.1, "input must not change"
    esri = gpd.GeoDataFrame({"geometry": [Point(-450000.0, -1250000.0)]}, crs="ESRI:102067")
    o2 = sjtsk.transform_gdf(esri, sjtsk.JTSK)
    assert o2.crs.to_epsg() == 5514 and o2.geometry.iloc[0].x == -450000.0


def test_other_notations_of_sjtsk():
    """EPSG:5513 (cadastral axes), 2065 (Ferro), 8352: same realization, only axes / prime meridian."""
    e, n = -450000.0, -1250000.0
    assert sjtsk.converter("EPSG:5513", sjtsk.JTSK)(-n, -e) == (e, n)
    a = sjtsk.converter("EPSG:2065", sjtsk.JTSK)(-n, -e)
    assert abs(a[0] - e) < 1e-6 and abs(a[1] - n) < 1e-6
    assert sjtsk.converter("EPSG:8352", sjtsk.JTSK)(-n, -e) == sjtsk.converter(sjtsk.JTSK03, sjtsk.JTSK)(e, n)
    x5513, y5513 = sjtsk.converter(sjtsk.ETRS89, "EPSG:5513")(19.0, 48.7)
    ee, nn = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)(19.0, 48.7)
    assert abs(x5513 + nn) < 1e-6 and abs(y5513 + ee) < 1e-6
