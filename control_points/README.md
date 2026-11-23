# Control points — format

One set = one folder with `points.csv` and `metadata.json`. Sets that may not be published belong outside the
repository; the functions take the folder path:

```python
from sjtsk import control_points as cp
s = cp.load("path/to/set")
results = cp.evaluate(s)                 # ugkk, sk3, sk4
print(cp.report(s, results))             # mean, RMSE, P95, max; the most accurate variant
cp.save_csv(results, "residuals.csv")    # point × variant: dE, dN, error
```

`example/` is a **synthetic** set (invented points, S-JTSK computed with variant `ugkk` + 2 cm noise) — it checks
the format and the computation, not the accuracy. It is written by `tools/make_example_points.py`.

## points.csv

UTF-8, **comma** separator, decimal **point**, header required. Slovak column names (`realizacia`, `etrs_b`,
`etrs_l`, `ramec`, `epocha`, `presnost_poloha_m`, `zdroj`, `nazov`, `poznamka`; file `body.csv`) are accepted too.

| column | required | meaning |
|---|---|---|
| `id` | yes | point identifier (unique in the set) |
| `name` | no | number of the national trigonometric / densification point, description |
| `sjtsk_y`, `sjtsk_x` | yes | S-JTSK in the **geodetic form** — positive Y, X in metres (Y ≈ 150–650 thousand, X ≈ 1.1–1.4 million) |
| `realization` | yes | `JTSK` or `JTSK03` |
| `etrs_lat`, `etrs_lon` | yes | latitude and longitude in decimal degrees, at least 9 decimals |
| `etrs_h` | no | ellipsoidal height [m] |
| `frame` | yes | `ETRF2000` (ETRS89 in Slovakia); `ITRF2020` / `ITRF2014` only with an epoch |
| `epoch` | for ITRF | decimal year of the measurement (e.g. 2026.85) |
| `position_accuracy_m` | yes | standard position error of the point [m] |
| `source` | yes | where the coordinates come from (ÚGKK database, SKPOS measurement, …) |
| `note` | no | |

**Mind the signs and the axes.** EPSG:5514 / 8353 have E = −Y and N = −X (negative numbers). The CSV holds the
positive Y, X a surveyor uses. Loading refuses negative values, swapped Y and X and swapped latitude and
longitude — with a message saying what is wrong.

Points in ITRF are not evaluated yet (they must first be converted to ETRF2000 with their epoch; the difference is
about 1.0 m today).

## metadata.json

```json
{
  "set": "ugkk_2026",
  "description": "identical points of the national network, coordinates from the ÚGKK database",
  "author": "…", "contact": "…", "date": "2026-12-01",
  "licence": "…", "publishable": false,
  "method": "…",
  "reference_transformation_according_to_author": "…"
}
```
