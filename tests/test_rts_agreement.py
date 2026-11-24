"""Agreement with the binding RTS service (METHODOLOGY.md, section 5.1), on the stored RTS output of 24 Nov 2026.

Guards the documented numbers: the grid step equals RTS within the rounding of its output, the Helmert step is a
constant 5.3 mm off, and QGIS 3.44's default operation is metres off. A change of the transformation shows here.
"""
import csv
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import compare_rts  # noqa: E402

D = ROOT / "validation" / "rts"


def _diff(kind, name, tmp_path):
    compare_rts.main(kind, str(D / name), out_dir=tmp_path)
    rows = list(csv.DictReader(open(tmp_path / f"result_{kind}.csv", encoding="utf-8")))
    a, b = ("dN_mm", "dE_mm") if kind == "etrs89" else ("dY_mm", "dX_mm")
    return rows, np.array([float(r[a]) for r in rows]), np.array([float(r[b]) for r in rows])


@pytest.mark.parametrize("kind,name", [("jtsk03", "rts_output_1_jtsk03.txt"), ("jtsk", "rts_output_2_jtsk.txt")])
def test_forward_constant_offset(tmp_path, kind, name):
    rows, dy, dx = _diff(kind, name, tmp_path)
    assert len(rows) == 56
    assert 4.8 < dx.mean() < 5.8 and 0.3 < dy.mean() < 1.1           # RTS 5.3 mm south, 0.7 mm west
    assert dx.std() < 0.45 and dy.std() < 0.45                         # = rounding of the RTS output (1 mm)
    assert np.hypot(dx, dy).max() < 6.5


def test_reverse_constant_offset(tmp_path):
    rows, dn, de = _diff("etrs89", "rts_output_3_etrs89.txt", tmp_path)
    assert len(rows) == 56
    assert -5.6 < dn.mean() < -4.8 and abs(de.mean()) < 0.6
    assert dn.std() < 0.2 and de.std() < 0.4
    assert np.hypot(dn, de).max() < 6.0


def test_grid_step_equals_rts(tmp_path):
    _, y03, x03 = _diff("jtsk03", "rts_output_1_jtsk03.txt", tmp_path)
    _, yj, xj = _diff("jtsk", "rts_output_2_jtsk.txt", tmp_path)
    assert np.hypot(yj - y03, xj - x03).max() < 1.5                    # two values rounded to 1 mm


def test_qgis_default_is_metres_off_rts(tmp_path):
    compare_rts.main("jtsk", str(D / "rts_output_2_jtsk.txt"), out_dir=tmp_path)
    q = np.array([float(r["qgis344_default_vs_rts_m"])
                  for r in csv.DictReader(open(tmp_path / "result_jtsk.csv", encoding="utf-8"))])
    assert 1.8 < q.mean() < 2.0 and 4.0 < q.max() < 4.2
