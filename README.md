# sjtsk

[![DOI](https://zenodo.org/badge/1468805361.svg)](https://doi.org/10.5281/zenodo.24477732)
[![tests](https://github.com/SimonSalon25/sjtsk/actions/workflows/tests.yml/badge.svg)](https://github.com/SimonSalon25/sjtsk/actions/workflows/tests.yml)

Slovak coordinates done the official way: **S-JTSK (JTSK, JTSK03) ↔ ETRS89 / WGS 84** with the transformation of
the Slovak Office of Geodesy, Cartography and Cadastre (ÚGKK) and the GKÚ grid — included, so the result does not
depend on how PROJ happens to be installed.

```python
import sjtsk

c = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)      # official chain (variant "ugkk")
e, n = c(19.15, 48.74)                               # lon, lat → E, N (EPSG:5514); scalars or numpy arrays
lon, lat = c.inverse(e, n)

sjtsk.converter(sjtsk.JTSK03, sjtsk.JTSK)(e, n)      # ZBGIS / DMR5 (JTSK03) → cadastre (JTSK), by the grid
sjtsk.converter("EPSG:5513", sjtsk.JTSK)(x, y)       # cadastral axes → EPSG:5514, no datum shift
sjtsk.transform_gdf(gdf, sjtsk.JTSK)                 # instead of gdf.to_crs()
sjtsk.identify('LOCAL_CS[..., AUTHORITY["EPSG","8353"]]')   # → JTSK03 (how the national DEM is written)
```

## Problem, state of the art and solution

**Problem.** Spatial data in Slovakia come in three coordinate systems: the cadastre in S-JTSK [JTSK] (EPSG:5514;
results delivered to the cadastre must be in JTSK, EPSG::5513, by ÚGKK regulation No. 300/2009 Coll., § 18(1), as
amended), the national datasets — topographic database
ZBGIS, elevation model DMR5, national forest maps — in S-JTSK [JTSK03] (EPSG:8353), and GNSS field data in ETRS89 or
WGS 84. Forest stands, cadastral parcels, field surveys and national rasters can be compared only if all of them are
transformed the same way. The official way is defined by ÚGKK: the Helmert transformation ETRS89 ↔ JTSK03 (EPSG 8365 /
8367) and the GKÚ grid JTSK03 ↔ JTSK (EPSG 8364); for work whose results go to the cadastre, the departmental
transformation service RTS (zbgis.skgeodesy.sk/rts) is binding (§ 2(10) of the same regulation).

**State as of 23 November 2026** (computed on 3,978 points covering Slovakia and tested in QGIS; [METHODOLOGY.md](METHODOLOGY.md)):
- common GIS software does not apply the official transformation reliably — PROJ picks "the best available"
  operation, and that depends on the installation;
- the same point given in ETRS89 or in WGS 84 ends up up to **1.36 m** apart; the usual WGS 84 parameters are up to
  **1.69 m** off the official result;
- JTSK03 data are often taken as JTSK, although the two differ by up to **1.64 m**;
- QGIS 3.44.12 (PROJ 9.8.1, Windows) transforms ETRS89 → EPSG:5514 with the Czech parameters "S-JTSK to ETRS89 (1)":
  off the official ÚGKK chain by **up to 4.2 m** (mean 1.9 m; 3.1–4.2 m in eastern Slovakia), confirmed in QGIS on
  12 test points (0.54–3.60 m); installing the GKÚ grid alone does not change this choice.

| variant | mean | max |
|---|---:|---:|
| `ugkk` — official ÚGKK chain with the GKÚ grid (default) | reference | |
| `sk3` — PROJ's choice for ETRS89 without the grid | 0.31 m | 1.12 m |
| `sk4` — PROJ's choice for WGS 84, the usual TOWGS84 | 0.68 m | 1.69 m |
| JTSK03 taken as JTSK | 0.69 m | 1.64 m |
| QGIS 3.44 default ETRS89 → 5514 — Czech parameters "S-JTSK to ETRS89 (1)" | 1.87 m | 4.18 m |

All figures are differences from the official ÚGKK chain as defined in EPSG (8442 / 8443) and implemented in PROJ
— a comparison of models on computed points, not an accuracy assessment.

**Check against the binding RTS service** (24 November 2026, 56 points across Slovakia, [`validation/rts/`](validation/rts/)):
the GKÚ grid step JTSK03 → JTSK agrees with RTS to the rounding of its output (≤ 1.1 mm). The Helmert step
ETRS89 ↔ JTSK03 differs by an almost constant **5.3 mm** (RTS lies 5.3 mm further south, standard deviation 0.3 mm =
the rounding of the RTS output, max 6.0 mm), in both directions. The EPSG pair used here and in PROJ (8365 forward,
8367 reverse) does not close on a round trip (10.6 mm); RTS behaves as one consistent transformation lying between
the two. Which parameters RTS uses is being clarified with GKÚ. For GIS, forestry and GNSS work the difference is
negligible; for results that go to the cadastre use RTS, which is binding. QGIS 3.44's default operation is
**1.91 m off RTS on average and up to 4.10 m**.

**Solution.** This library implements the official ÚGKK chain with the GKÚ grid included, so the result does not
depend on how PROJ is installed (equal to PROJ with the official grid to below 0.01 mm); one path for ETRS89 and
WGS 84; JTSK03 recognised and transformed, also when written as `LOCAL_CS` (DMR5); the variant is always explicit
(`converter(src, dst, "sk4")` to compare or to match old data). The QGIS plugin
[S-JTSK Official Transformation](https://github.com/SimonSalon25/qgis-plugins) brings the same transformation to QGIS
and sets it as QGIS's preferred one.

**Aim.** Forest stand boundaries, cadastral parcels, GNSS field data and national rasters in Slovakia should match
at the level of the official transformation (within millimetres) regardless of the software and its installation — with
an open, reproducible method that others can check and reuse.

Also included:
- **control points** — a format for identical points and an evaluation of all variants against them
  (`sjtsk.control_points`, `control_points/README.md`);
- **a portable implementation** in pure Python (no PROJ) and a binary grid format, as a reference for ports to other
  languages (used by a Flutter mobile app) — `sjtsk.portable`, `tools/export_portable.py`.

## Install and test

```bash
pip install "sjtsk @ git+https://github.com/SimonSalon25/sjtsk"        # numpy, pyproj (not on PyPI yet)
pip install "sjtsk[geo] @ git+https://github.com/SimonSalon25/sjtsk"   # + shapely / geopandas for geometries
pip install -e ".[test]" && pytest && python tools/mutations.py
python tools/compare_variants.py     # reproduces the table above
```

## How it was made

Written with an AI assistant under the direction of the author, who defined the problem, made the decisions and
tested the results; see [AI_DISCLOSURE.md](AI_DISCLOSURE.md).

## Funding

Developed within the project **APVV-23-0289** *Increasing the operational reliability of linear power structures by using data from remote sensing*, supported by the Slovak Research and Development Agency (APVV).

## Licence

Code: MIT (`LICENSE`). The GKÚ grid `src/sjtsk/data/sk_gku_JTSK03_to_JTSK.tif`: © 2013 GKÚ Bratislava,
CC BY 4.0 (`src/sjtsk/data/sk_gku_LICENSE.txt`).
