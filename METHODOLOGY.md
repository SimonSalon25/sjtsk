# Methodology

What the package does, why, and how each number was obtained — so that the results can be reproduced and criticised.
All numbers below are reproduced by `python tools/compare_variants.py` and guarded by the tests.

## 1. The problem

Slovak data come in two realizations of the S-JTSK system: **JTSK** (EPSG:5514; cadastre — Slovak regulation
ÚGKK 300/2009 § 18 requires results for the cadastre in the JTSK realization, EPSG::5513) and **JTSK03**
(EPSG:8353; national topographic database ZBGIS, the DMR5 elevation model, national forest maps).
GNSS gives ETRS89 or WGS 84. A GIS application must therefore transform between four systems — and the result
depends on which transformation PROJ picks:

| where (application before the fix) | transformation | what PROJ actually picks (pip pyproj, no grid, no network) |
|---|---|---|
| GPS position, status bar | 5514 ↔ 4258 | **S-JTSK to ETRS89 (3)** — Molodensky-Badekas |
| boundaries from a WFS (WGS 84), geopandas `to_crs` | 4326 → 5514 | **S-JTSK to WGS 84 (4)** — 7-parameter Helmert |
| mobile app (TOWGS84 in WKT) | — | = (4) |
| rasters in JTSK03 | 8353 = 5514 | no transformation (JTSK03 taken as JTSK) |

Findings:

1. **Two paths, one point, two positions.** ETRS89 and WGS 84 were treated as practically identical, yet PROJ
   picks a different operation for each; they differ by 0.61 m on average and up to 1.36 m.
2. **The choice depends on the installation.** With the official grid in the PROJ data directory, the ETRS89 path
   switches to the official chain (millimetres) while the WGS 84 path stays on (4). Without the grid (pip pyproj,
   network disabled) ETRS89 goes through (3). QGIS with another PROJ version may choose differently. The result is
   not reproducible from the code alone.
3. **JTSK and JTSK03 differ by decimetres to metres**, not "decimetres at most": 0.69 m on average, up to 1.64 m
   (south-west, near Bratislava), at least 0.02 m (Orava / Liptov) — see `docs/jtsk03_jtsk_difference.png`
   (`tools/plot_difference.py`).
4. **WGS 84 today ≠ ETRS89 by ~1 m** (ITRF2020 at epoch 2026.9 versus ETRF2000: 1.01 m in Bratislava and Košice).
   Irrelevant for phone GNSS (3–5 m), relevant for a paper on transformation accuracy.

## 2. The official chain (variant `ugkk`, the default)

ETRS89 → JTSK03 by the ÚGKK Helmert transformation (EPSG:8365, coordinate frame, declared accuracy 1 mm), then
JTSK03 → JTSK by the GKÚ grid `sk_gku_JTSK03_to_JTSK.tif` (EPSG:8364, bilinear). In EPSG this is "ETRS89 to S-JTSK
(5)" (EPSG:8442). The reverse direction is "S-JTSK to ETRS89 (6)" (EPSG:8443) with its own Helmert parameters
(EPSG:8367) published by ÚGKK — not the algebraic inverse of 8365 (the difference is up to 6 mm; a round trip
closes to 1.1 cm).

The grid (183,132 bytes, © 2013 GKÚ Bratislava, CC BY 4.0, from the OSGeo PROJ-data project) is **included** and
used by an absolute path in the PROJ pipeline, so the result does not depend on the PROJ installation and the global
PROJ state is not changed. The variant equals PROJ with the grid installed to 0.0000 mm (tested on 3,978 points,
both directions, and JTSK03 → JTSK).

Rules:
- WGS 84 and ETRS89 go to S-JTSK by the **same** path (WGS 84 ≡ ETRS89, zero shift, stated in the docs).
- JTSK ↔ JTSK03 always by the grid, directly — never through ETRS89.
- Other notations of the same datum (EPSG:5513 with positive south/west axes, 2065 Ferro, 8352) are converted by a
  pure change of axes / prime meridian, with no datum shift (going through ETRS89 instead introduced 0.14 m).
- A point outside the grid (outside Slovakia) gets the Helmert only, and the converter counts it (`outside_grid`) —
  never a silent switch to another result.
- `LOCAL_CS[... AUTHORITY["EPSG","8353"]]` (how the national DEM is written) is recognised as JTSK03; the code is taken
  only from the top-level AUTHORITY at the end of the WKT (a GeoTIFF drops it, and the last AUTHORITY then belongs to
  the unit, 9001).

## 3. Comparison of variants on Slovak territory

Reference: variant `ugkk`. Points: 3,978 in a regular grid of 0.05° × 0.03° inside an approximate outline of
Slovakia. Difference = distance in the Křovák plane [m].

| variant | mean | median | P95 | max |
|---|---:|---:|---:|---:|
| **sk3** — S-JTSK to ETRS89 (3), Molodensky-Badekas, EPSG:4829 (PROJ default for ETRS89 without the grid) | 0.310 | 0.269 | 0.722 | 1.120 |
| **sk4** — S-JTSK to ETRS89 / WGS 84 (4), Helmert 7p, EPSG:4827 / 4836 (PROJ for WGS 84; the usual TOWGS84) | 0.681 | 0.702 | 1.232 | 1.692 |
| JTSK03 taken as JTSK | 0.687 | 0.719 | 1.198 | 1.637 |
| S-JTSK to WGS 84 (1) — Czech parameters, old TOWGS84 in many GIS | 1.866 | 1.680 | 3.647 | 4.182 |
| S-JTSK to WGS 84 (3) — translation only | 6.873 | 5.803 | 14.164 | 15.685 |

Notes:
- sk4 is essentially the JTSK03 key applied directly to JTSK, so its error is almost the JTSK03–JTSK difference.
- The accuracies declared in EPSG (0.5 m for (3), 1 m for (4)) roughly match the P95, not the maximum.
- **This is a comparison with a model, not with measurements.** GKÚ states that the grid describes the systematic
  inhomogeneity of the JTSK network, not local inhomogeneities at the centimetre level, and recommends verification
  with the official service (zbgis.skgeodesy.sk/rts). The real accuracy will be shown by control points (section 5).

**Spatial variation of the JTSK03 → JTSK shift** (relevant when a raster is shifted by a constant amount at the
centre of a window): within 1 km at most 3 cm, 2 km 7 cm, 5 km 14 cm, 10 km 21 cm, 25 km 36 cm, 50 km 54 cm.

**Effect of ellipsoidal height** (the plane result is computed at h = 0): below 6.5 mm at 1,500 m and below 12 mm at
2,600 m (the highest point of Slovakia).

## 4. Portable implementation

`sjtsk.portable` is the same chain in pure Python (`math` only) with the grid in a simple binary format, as a
reference for ports to languages without PROJ (a Dart/Flutter mobile application uses it line by line). It agrees
with the PROJ-based converter to better than 0.01 mm on all 3,978 points (forward, inverse, JTSK03 shift).
`tools/export_portable.py` writes the grid and 20 reference points for testing a port.

## 5. Control points

The package defines a format for identical points (S-JTSK and ETRS89 coordinates of the same physical point,
`control_points/README.md`) and evaluates all variants against them (mean, RMSE, P95, max; the most accurate
variant). The included set is synthetic and checks only the format and the computation. Real control points
(national trigonometric network, SKPOS measurements) are the next step and would turn section 3 from a
model comparison into an accuracy assessment.

## 6. Verification

| claim | test |
|---|---|
| `ugkk` = PROJ with the official grid | 3,978 points, both directions and JTSK03 → JTSK, < 0.01 mm |
| `sk3`, `sk4` are exactly the EPSG operations | compared with the PROJ operations of the same name |
| the table in section 3 | recomputed and compared to ±2 mm |
| one path for WGS 84 and ETRS89 | identical results |
| other notations of S-JTSK | 5513, 2065, 8352: pure axis conversion |
| outside the grid | counted, Helmert only, finite |
| recognising systems | EPSG, ESRI, WKT1/WKT2, LOCAL_CS, pyproj and rasterio objects |
| control point input | swapped axes, negative E/N, swapped lat/lon, missing epoch, duplicates, decimal comma, missing column |
| portable implementation | equals the converter on 3,978 points |
| the tests themselves | `tools/mutations.py`: 12 deliberate bugs, each makes the suite fail |
