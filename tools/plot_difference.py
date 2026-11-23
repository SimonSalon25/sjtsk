"""Figure: magnitude of the JTSK03 → JTSK shift (GKÚ grid) over Slovakia, in the Křovák plane.

    python tools/plot_difference.py docs/jtsk03_jtsk_difference.png
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from shapely import contains_xy  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

import sjtsk  # noqa: E402
from slovakia import OUTLINE  # noqa: E402

lon, lat = np.meshgrid(np.arange(16.8, 22.6, 0.01), np.arange(47.7, 49.65, 0.006))
inside = contains_xy(Polygon(OUTLINE), lon, lat)
e, n = sjtsk.converter(sjtsk.ETRS89, sjtsk.JTSK03)(lon[inside], lat[inside])
dx, dy = sjtsk.jtsk03_to_jtsk_shift(e, n)
d = np.hypot(dx, dy)
fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
sc = ax.scatter(-e / 1000, -n / 1000, c=d, s=1.2, cmap="viridis", vmin=0, vmax=1.7, linewidths=0)
ax.set_aspect("equal")
ax.invert_xaxis()
ax.invert_yaxis()
ax.set_xlabel("S-JTSK Y [km]")
ax.set_ylabel("S-JTSK X [km]")
ax.set_title(f"JTSK03 → JTSK shift (GKÚ grid, EPSG:8364): mean {d.mean():.2f} m, max {d.max():.2f} m")
fig.colorbar(sc, ax=ax, label="shift [m]", shrink=0.85)
fig.tight_layout()
fig.savefig(sys.argv[1])
print(f"{sys.argv[1]}: {d.size} points, mean {d.mean():.3f} m, min {d.min():.3f} m, max {d.max():.3f} m")
