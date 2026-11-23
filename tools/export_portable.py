"""Files for a port of the transformation to another language:

    python tools/export_portable.py <target folder>

writes
  sk_gku_JTSK03_to_JTSK.lmg    the GKÚ grid in the portable binary format (sjtsk.portable)
  sk_gku_LICENSE.txt           the grid licence (CC BY 4.0)
  reference_points.json        20 points computed by this package (= PROJ with the grid): forward, inverse, shift

A port passes if it reproduces the points to better than 1 mm.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import sjtsk  # noqa: E402

#: towns + corners and inside of Slovakia (lat, lon) — the same on every run
POINTS = [(48.1486, 17.1077), (48.7363, 19.1462), (48.7164, 21.2611), (49.05, 22.5), (49.22, 18.74),
          (49.1, 20.3), (48.3, 19.6), (48.06, 17.1), (49.17, 19.35), (48.38, 17.6), (49.55, 19.3),
          (48.6, 22.1), (47.8, 18.2), (48.9, 20.8), (49.4, 21.6), (48.15, 18.9), (49.0, 17.5),
          (48.55, 20.2), (49.3, 22.2), (48.7, 17.8)]


def reference() -> dict:
    lat = [p[0] for p in POINTS]
    lon = [p[1] for p in POINTS]
    c = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK)
    e, n = c(lon, lat)
    lon2, lat2 = c.inverse(e, n)
    e3, n3 = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK03)(lon, lat)
    dx, dy = sjtsk.jtsk03_to_jtsk_shift(e3, n3)
    return {"generator": f"sjtsk {sjtsk.__version__}, tools/export_portable.py", "variant": "ugkk",
            "forward_etrs89_to_5514": [[a, b, float(x), float(y)] for a, b, x, y in zip(lat, lon, e, n)],
            "inverse_5514_to_etrs89": [[float(x), float(y), float(a), float(b)] for x, y, a, b in zip(e, n, lat2, lon2)],
            "shift_8353_to_5514": [[float(x), float(y), float(a), float(b)] for x, y, a, b in zip(e3, n3, dx, dy)]}


def main(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    sjtsk.portable.write_grid(sjtsk.grid_path(), target / "sk_gku_JTSK03_to_JTSK.lmg")
    shutil.copy(sjtsk.grid_path().parent / "sk_gku_LICENSE.txt", target / "sk_gku_LICENSE.txt")
    (target / "reference_points.json").write_text(json.dumps(reference(), indent=1), encoding="utf-8")
    print(f"grid, licence and {len(POINTS)} reference points → {target}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
