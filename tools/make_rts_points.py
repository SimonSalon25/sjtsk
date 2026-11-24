"""Points for the independent check against the official RTS service (METHODOLOGY.md, section 5.1).

    python tools/make_rts_points.py            # writes validation/rts/

56 ETRS89 points spread over Slovakia: the extremes that matter (largest and smallest JTSK03–JTSK difference,
the far west, east, north and south, the largest error of QGIS's default operation) and the rest chosen by
farthest-point sampling, so the whole territory is covered. Every point lies at least ~5 km inside an approximate
outline of Slovakia and inside the GKÚ grid. Deterministic: running it again gives the same files.

Written files (validation/rts/):
    points_etrs89.txt          id;latitude;longitude (decimal degrees, 9 decimals; Windows line ends) — RTS input, run 1 and 2
    rts_input_etrs89.zip       the same file zipped (RTS accepts only .zip)
    points_jtsk.txt            id;Y;X in JTSK (EPSG:5513, positive, metres, 4 decimals) — RTS input, run 3
    rts_input_jtsk.zip         the same file zipped
    expected.csv               what this package gives for every point (and what QGIS 3.44's default gives)
"""
import csv
import sys
import warnings
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # a Windows console (cp1252) cannot print → or – and would fail
    sys.stdout.reconfigure(errors="replace")

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
import sjtsk  # noqa: E402
from slovakia import OUTLINE  # noqa: E402

N_POINTS = 56
OUT = ROOT / "validation" / "rts"


def candidates():
    from shapely import contains_xy
    from shapely.geometry import Polygon
    inner = Polygon(OUTLINE).buffer(-0.06)          # ~5 km inside the approximate outline
    lon, lat = np.meshgrid(np.arange(16.80, 22.60, 0.02), np.arange(47.70, 49.65, 0.0125))
    lon, lat = lon.ravel(), lat.ravel()
    rng = np.random.default_rng(20261124)           # small deterministic jitter: no round coordinates
    lon = lon + rng.uniform(-0.004, 0.004, lon.size)
    lat = lat + rng.uniform(-0.003, 0.003, lat.size)
    m = contains_xy(inner, lon, lat)
    return np.round(lon[m], 9), np.round(lat[m], 9)


def czech_default(lon, lat):
    """What QGIS 3.44 used by default for ETRS89 → EPSG:5514: inverse of 'S-JTSK to ETRS89 (1)'."""
    from pyproj.transformer import TransformerGroup
    with warnings.catch_warnings():                 # "best transformation (Czech grid) not available" is the point
        warnings.simplefilter("ignore")
        group = TransformerGroup("EPSG:4258", "EPSG:5514", always_xy=True).transformers
    t = [t for t in group if t.description.startswith("Inverse of S-JTSK to ETRS89 (1) ")]
    if not t:
        return None
    return t[0].transform(lon, lat)


def select(lon, lat, e03, n03, e, n):
    shift = np.hypot(e - e03, n - n03)
    cz = czech_default(lon, lat)
    picks = [int(np.argmax(shift)), int(np.argmin(shift)), int(np.argmin(lon)), int(np.argmax(lon)),
             int(np.argmax(lat)), int(np.argmin(lat))]
    if cz is not None:
        picks.append(int(np.argmax(np.hypot(np.asarray(cz[0]) - e, np.asarray(cz[1]) - n))))
    chosen = list(dict.fromkeys(picks))
    # farthest-point sampling in the plane (metres)
    xy = np.column_stack([e, n])
    d = np.min(np.linalg.norm(xy[:, None, :] - xy[chosen][None, :, :], axis=2), axis=1)
    while len(chosen) < N_POINTS:
        i = int(np.argmax(d))
        chosen.append(i)
        d = np.minimum(d, np.linalg.norm(xy - xy[i], axis=1))
    # order west → east for readability
    return sorted(chosen, key=lambda i: (round(lon[i], 1), -lat[i]))


def main():
    lon, lat = candidates()
    to03 = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK03)
    toj = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)
    e03, n03 = to03(lon, lat)
    e, n = toj(lon, lat)
    idx = select(lon, lat, e03, n03, e, n)
    lon, lat, e03, n03, e, n = (np.asarray(a)[idx] for a in (lon, lat, e03, n03, e, n))

    toj = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)  # fresh counter for the selected points
    toj(lon, lat)
    assert toj.outside_grid == 0, "a point lies outside the GKÚ grid"

    # run 3 input: JTSK as RTS shows it (EPSG:5513, positive Y, X), rounded to 0.1 mm
    y_in, x_in = np.round(-e, 4), np.round(-n, 4)
    lon_back, lat_back = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK).inverse(-y_in, -x_in)
    cz = czech_default(lon, lat)

    OUT.mkdir(parents=True, exist_ok=True)
    ids = [f"RTS{i + 1:02d}" for i in range(len(idx))]
    with open(OUT / "points_etrs89.txt", "w", encoding="utf-8", newline="") as f:
        f.write("id;latitude;longitude\r\n")
        for k, la, lo in zip(ids, lat, lon):
            f.write(f"{k};{la:.9f};{lo:.9f}\r\n")
    with open(OUT / "points_jtsk.txt", "w", encoding="utf-8", newline="") as f:
        f.write("id;Y;X\r\n")
        for k, y, x in zip(ids, y_in, x_in):
            f.write(f"{k};{y:.4f};{x:.4f}\r\n")
    for name, member in (("rts_input_etrs89.zip", "points_etrs89.txt"), ("rts_input_jtsk.zip", "points_jtsk.txt")):
        with zipfile.ZipFile(OUT / name, "w", zipfile.ZIP_DEFLATED) as z:
            info = zipfile.ZipInfo(member, date_time=(2026, 11, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (OUT / member).read_bytes())

    cols = ["id", "latitude", "longitude", "jtsk03_Y", "jtsk03_X", "jtsk_Y", "jtsk_X", "jtsk03_jtsk_shift_m",
            "back_latitude", "back_longitude", "qgis344_default_jtsk_Y", "qgis344_default_jtsk_X",
            "qgis344_default_error_m"]
    with open(OUT / "expected.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, k in enumerate(ids):
            row = [k, f"{lat[i]:.9f}", f"{lon[i]:.9f}", f"{-e03[i]:.4f}", f"{-n03[i]:.4f}", f"{-e[i]:.4f}",
                   f"{-n[i]:.4f}", f"{np.hypot(e[i] - e03[i], n[i] - n03[i]):.4f}", f"{lat_back[i]:.10f}",
                   f"{lon_back[i]:.10f}"]
            if cz is not None:
                row += [f"{-cz[0][i]:.4f}", f"{-cz[1][i]:.4f}", f"{np.hypot(cz[0][i] - e[i], cz[1][i] - n[i]):.4f}"]
            else:
                row += ["", "", ""]
            w.writerow(row)
    shift = np.hypot(e - e03, n - n03)
    print(f"{len(ids)} points → {OUT}")
    print(f"longitude {lon.min():.3f}–{lon.max():.3f}, latitude {lat.min():.3f}–{lat.max():.3f}")
    print(f"JTSK03–JTSK difference {shift.min():.3f}–{shift.max():.3f} m")
    if cz is not None:
        err = np.hypot(np.asarray(cz[0]) - e, np.asarray(cz[1]) - n)
        print(f"QGIS 3.44 default (Czech parameters) off the official chain: {err.min():.2f}–{err.max():.2f} m")


if __name__ == "__main__":
    main()
