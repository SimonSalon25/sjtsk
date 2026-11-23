"""Table of ETRS89 → S-JTSK variants on Slovak territory (METHODOLOGY.md, section 3).

    python tools/compare_variants.py      # reference = variant ugkk (official ÚGKK chain)
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
import sjtsk  # noqa: E402
from slovakia import points  # noqa: E402

lon, lat = points()
ref = np.array(sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)(lon, lat))
print(f"{lon.size} points in Slovakia, difference from ugkk in the Křovák plane [m]\n")
print(f"{'variant':38s} {'mean':>8s} {'median':>8s} {'P95':>8s} {'max':>8s}")
rows = [("sk3 (PROJ without grid, for ETRS89)", sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK, "sk3")(lon, lat)),
        ("sk4 (PROJ for WGS 84, common TOWGS84)", sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK, "sk4")(lon, lat)),
        ("JTSK03 taken as JTSK", sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK03)(lon, lat)),
        ("proj_auto (this installation)", sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK, "proj_auto")(lon, lat))]
from pyproj.transformer import TransformerGroup  # noqa: E402

group = TransformerGroup("EPSG:4326", "EPSG:5514", always_xy=True).transformers
for title, label in (("S-JTSK to WGS 84 (1)", "CZ (1), old TOWGS84 in many GIS"),
                     ("S-JTSK to WGS 84 (3)", "WGS 84 (3), translation only")):
    t = [t for t in group if title in t.description][0]
    rows.append((label, t.transform(lon, lat)))
for name, (e, n) in rows:
    d = np.hypot(e - ref[0], n - ref[1])
    print(f"{name:38s} {d.mean():8.3f} {np.median(d):8.3f} {np.percentile(d, 95):8.3f} {d.max():8.3f}")
