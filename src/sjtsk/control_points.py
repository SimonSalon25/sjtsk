"""Control (identical) points: loading, checking, and evaluating the transformation variants.

A set = a folder with `points.csv` and `metadata.json` (format in `control_points/README.md`).
S-JTSK in the CSV is in the geodetic form (positive Y, X); EPSG:5514/8353 has E = −Y, N = −X. The package does
the conversion — swapped axes or signs are the most common error when exchanging data, and they are refused.
Slovak column names (as used in the Slovak version of the format) are accepted too.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import crs as _c
from .transform import converter

REQUIRED = ("id", "sjtsk_y", "sjtsk_x", "realization", "etrs_lat", "etrs_lon", "frame", "position_accuracy_m",
            "source")
FRAMES = ("ETRF2000", "ITRF2020", "ITRF2014")
#: Slovak column names → English (files written for the Slovak applications)
SLOVAK_COLUMNS = {"nazov": "name", "realizacia": "realization", "etrs_b": "etrs_lat", "etrs_l": "etrs_lon",
                  "ramec": "frame", "epocha": "epoch", "presnost_poloha_m": "position_accuracy_m", "zdroj": "source",
                  "poznamka": "note"}


class ControlPointError(ValueError):
    """The point set is invalid; the message says which row and what is wrong."""


@dataclass(frozen=True)
class Point:
    id: str
    y: float                 # S-JTSK Y (positive, geodetic form)
    x: float                 # S-JTSK X (positive)
    realization: str         # JTSK / JTSK03
    lat: float               # latitude [°]
    lon: float               # longitude [°]
    frame: str
    accuracy_m: float
    source: str
    name: str = ""
    h: float | None = None
    epoch: float | None = None
    note: str = ""

    @property
    def crs(self) -> _c.Crs:
        return _c.JTSK if self.realization == "JTSK" else _c.JTSK03

    @property
    def en(self) -> tuple[float, float]:
        """(E, N) in EPSG:5514 / 8353."""
        return -self.y, -self.x


@dataclass
class PointSet:
    name: str
    points: list[Point]
    metadata: dict = field(default_factory=dict)


def _number(row, column, line, required=True):
    value = (row.get(column) or "").strip()
    if not value:
        if required:
            raise ControlPointError(f"row {line}: {column} is missing")
        return None
    try:
        return float(value)
    except ValueError:
        raise ControlPointError(f"row {line}: {column}={value!r} is not a number "
                                "(decimal point, comma as separator)") from None


def load(folder) -> PointSet:
    """Load and check `points.csv` (or `body.csv`) and `metadata.json` from a folder."""
    folder = Path(folder)
    path = folder / "points.csv"
    if not path.is_file() and (folder / "body.csv").is_file():
        path = folder / "body.csv"
    if not path.is_file():
        raise ControlPointError(f"{folder / 'points.csv'} is missing")
    metadata = {}
    if (folder / "metadata.json").is_file():
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    points, seen = [], set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = [SLOVAK_COLUMNS.get(c, c) for c in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in fields]
        if missing:
            raise ControlPointError(f"columns missing in the header: {', '.join(missing)}")
        for i, raw in enumerate(reader, start=2):
            r = {SLOVAK_COLUMNS.get(k, k): v for k, v in raw.items()}
            pid = (r["id"] or "").strip()
            if not pid or pid in seen:
                raise ControlPointError(f"row {i}: id {pid!r} is missing or repeated")
            seen.add(pid)
            realization = r["realization"].strip().upper()
            if realization not in ("JTSK", "JTSK03"):
                raise ControlPointError(f"row {i}: realization must be JTSK or JTSK03, not {realization!r}")
            frame = r["frame"].strip().upper()
            if frame not in FRAMES:
                raise ControlPointError(f"row {i}: frame {frame!r}; known {', '.join(FRAMES)}")
            y, x = _number(r, "sjtsk_y", i), _number(r, "sjtsk_x", i)
            if not (150_000 <= y <= 650_000 and 1_100_000 <= x <= 1_400_000):
                raise ControlPointError(f"row {i}: S-JTSK Y={y}, X={x} outside Slovakia — expected positive "
                                        "Y≈150–650 thousand, X≈1.1–1.4 million (swapped axes? negative E/N "
                                        "from EPSG:5514?)")
            lat, lon = _number(r, "etrs_lat", i), _number(r, "etrs_lon", i)
            if not (47.5 <= lat <= 49.8 and 16.5 <= lon <= 22.8):
                raise ControlPointError(f"row {i}: lat={lat}, lon={lon} outside Slovakia "
                                        "(swapped latitude and longitude?)")
            epoch = _number(r, "epoch", i, required=False)
            if frame != "ETRF2000" and epoch is None:
                raise ControlPointError(f"row {i}: the epoch is required for frame {frame}")
            points.append(Point(id=pid, y=y, x=x, realization=realization, lat=lat, lon=lon, frame=frame,
                                accuracy_m=_number(r, "position_accuracy_m", i), source=r["source"].strip(),
                                name=(r.get("name") or "").strip(), h=_number(r, "etrs_h", i, required=False),
                                epoch=epoch, note=(r.get("note") or "").strip()))
    if not points:
        raise ControlPointError(f"{path}: no points")
    return PointSet(name=metadata.get("set", metadata.get("sada", folder.name)), points=points, metadata=metadata)


@dataclass
class Result:
    variant: str
    points: list[tuple[str, float, float, float]]   # id, dE, dN, position error [m]; computed − given

    @property
    def errors(self) -> np.ndarray:
        return np.array([p[3] for p in self.points])

    def summary(self) -> dict:
        d = self.errors
        return {"variant": self.variant, "points": int(d.size), "mean": float(d.mean()),
                "rmse": float(math.sqrt((d ** 2).mean())), "p95": float(np.percentile(d, 95)),
                "max": float(d.max())}


def evaluate(point_set: PointSet, variants=("ugkk", "sk3", "sk4")) -> list[Result]:
    """For every variant: ETRS89 of the point → S-JTSK of its realization, compared with the given coordinates.

    Points in another frame than ETRF2000 are not evaluated (convert them with their epoch first).
    """
    used = [p for p in point_set.points if p.frame == "ETRF2000"]
    if not used:
        raise ControlPointError("no point in ETRF2000 — convert other frames with their epoch first")
    results = []
    for name in variants:
        rows = []
        for system in (_c.JTSK, _c.JTSK03):
            group = [p for p in used if p.crs is system]
            if not group:
                continue
            e, n = converter(_c.ETRS89, system, name)(np.array([p.lon for p in group]),
                                                       np.array([p.lat for p in group]))
            for p, ee, nn in zip(group, e, n):
                de, dn = ee - p.en[0], nn - p.en[1]
                rows.append((p.id, float(de), float(dn), float(math.hypot(de, dn))))
        results.append(Result(name, rows))
    return results


def best(results: list[Result], criterion: str = "rmse") -> Result:
    return min(results, key=lambda r: r.summary()[criterion])


def report(point_set: PointSet, results: list[Result]) -> str:
    lines = [f"Set {point_set.name}: {len(point_set.points)} points", "",
             f"{'variant':10s} {'points':>6s} {'mean':>8s} {'RMSE':>8s} {'P95':>8s} {'max':>8s}  [m]"]
    for r in results:
        s = r.summary()
        lines.append(f"{s['variant']:10s} {s['points']:6d} {s['mean']:8.3f} {s['rmse']:8.3f} "
                     f"{s['p95']:8.3f} {s['max']:8.3f}")
    lines += ["", f"most accurate by RMSE: {best(results).variant}"]
    return "\n".join(lines)


def save_csv(results: list[Result], path) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "variant", "dE_m", "dN_m", "error_m"])
        for r in results:
            for pid, de, dn, d in r.points:
                w.writerow([pid, r.variant, f"{de:.4f}", f"{dn:.4f}", f"{d:.4f}"])
