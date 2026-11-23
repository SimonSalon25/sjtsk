# sjtsk

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

**Problem.** Spatial data in Slovakia come in three coordinate systems: the cadastre in S-JTSK [JTSK] (EPSG:5514,
required for cadastral deliveries by ÚGKK regulation 300/2009 § 18), the national datasets — topographic database
ZBGIS, elevation model DMR5, national forest maps — in S-JTSK [JTSK03] (EPSG:8353), and GNSS field data in ETRS89 or
WGS 84. Forest stands, cadastral parcels, field surveys and national rasters can be compared only if all of them are
transformed the same way. The official way is defined by ÚGKK: the Helmert transformation ETRS89 ↔ JTSK03 (EPSG 8365 /
8367) and the GKÚ grid JTSK03 ↔ JTSK (EPSG 8364).

**State as of 23 November 2026** (measured on 3,978 points covering Slovakia and in QGIS; [METHODOLOGY.md](METHODOLOGY.md)):
- common GIS software does not apply the official transformation reliably — PROJ picks "the best available"
  operation, and that depends on the installation;
- the same point given in ETRS89 or in WGS 84 ends up up to **1.36 m** apart; the usual WGS 84 parameters are up to
  **1.69 m** off the official result;
- JTSK03 data are often taken as JTSK, although the two differ by up to **1.64 m**;
- QGIS 3.44.12 (PROJ 9.8.1, Windows) transforms ETRS89 → EPSG:5514 with the Czech parameters "S-JTSK to ETRS89 (1)":
  **0.5 m in western to 3.6 m in eastern Slovakia** off the official result; installing the GKÚ grid alone does not
  change this choice.

| variant | mean | max |
|---|---:|---:|
| `ugkk` — official ÚGKK chain with the GKÚ grid (default) | reference | |
| `sk3` — PROJ's choice for ETRS89 without the grid | 0.31 m | 1.12 m |
| `sk4` — PROJ's choice for WGS 84, the usual TOWGS84 | 0.68 m | 1.69 m |
| JTSK03 taken as JTSK | 0.69 m | 1.64 m |
| QGIS 3.44 default ETRS89 → 5514 (Czech parameters), 12 control points | — | 3.60 m |

**Solution.** This library implements the official ÚGKK chain with the GKÚ grid included, so the result does not
depend on how PROJ is installed (equal to PROJ with the official grid to below 0.01 mm); one path for ETRS89 and
WGS 84; JTSK03 recognised and transformed, also when written as `LOCAL_CS` (DMR5); the variant is always explicit
(`converter(src, dst, "sk4")` to compare or to match old data). The QGIS plugin
[S-JTSK Official Transformation](https://github.com/SimonSalon25/qgis-plugins) brings the same transformation to QGIS
and sets it as QGIS's preferred one.

**Aim.** Forest stand boundaries, cadastral parcels, GNSS field data and national rasters in Slovakia should match
at the level of the official transformation (millimetres) regardless of the software and its installation — with
an open, reproducible method that others can check and reuse.

Also included:
- **control points** — a format for identical points and an evaluation of all variants against them
  (`sjtsk.control_points`, `control_points/README.md`);
- **a portable implementation** in pure Python (no PROJ) and a binary grid format, as a reference for ports to other
  languages (used by a Flutter mobile app) — `sjtsk.portable`, `tools/export_portable.py`.

## Install and test

```bash
pip install sjtsk                    # numpy, pyproj
pip install "sjtsk[geo]"             # + shapely / geopandas for geometries
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
