"""Writes the SYNTHETIC example set control_points/example — invented points, no third-party data.

S-JTSK is computed with the official chain (ugkk) plus ±2 cm noise, so ugkk must win the evaluation. The set only
checks the format and the computation, not the accuracy.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import sjtsk  # noqa: E402

rng = np.random.default_rng(560)
coords = [(17.12, 48.15), (17.60, 48.40), (18.10, 48.30), (18.75, 49.22), (19.15, 48.74), (19.60, 49.08),
          (20.30, 49.06), (20.75, 48.70), (21.26, 48.72), (21.65, 49.00), (22.10, 48.95), (18.50, 48.00)]
rows = []
for i, (lon, lat) in enumerate(coords, start=1):
    crs = sjtsk.JTSK03 if i % 2 else sjtsk.JTSK
    e, n = sjtsk.converter(sjtsk.ETRS89, crs)(lon, lat)
    e += rng.normal(0, 0.02)
    n += rng.normal(0, 0.02)
    rows.append({"id": f"E{i:02d}", "name": f"invented point {i}", "sjtsk_y": f"{-e:.3f}", "sjtsk_x": f"{-n:.3f}",
                 "realization": crs.realization, "etrs_lat": f"{lat:.9f}", "etrs_lon": f"{lon:.9f}", "etrs_h": "",
                 "frame": "ETRF2000", "epoch": "", "position_accuracy_m": "0.02", "source": "synthetic",
                 "note": "format test only"})
target = ROOT / "control_points" / "example"
target.mkdir(parents=True, exist_ok=True)
with (target / "points.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
(target / "metadata.json").write_text(json.dumps({
    "set": "example", "description": "synthetic points for testing the format — S-JTSK computed with ugkk + 2 cm noise",
    "author": "sjtsk", "contact": "", "date": "2026-11-22", "licence": "CC0", "publishable": True,
    "method": "tools/make_example_points.py", "reference_transformation_according_to_author": "ugkk"},
    ensure_ascii=False, indent=2), encoding="utf-8")
print("written", target)
