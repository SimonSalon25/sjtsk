"""tools/compare_rts.py reads RTS output in any of the text layouts RTS offers and matches it to the expected values."""
import csv
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import compare_rts  # noqa: E402

EXPECTED = list(csv.DictReader(open(ROOT / "validation" / "rts" / "expected.csv", encoding="utf-8")))


def _write(path, rows, sep, comma, header):
    fmt = (lambda v: v.replace(".", ",")) if comma else (lambda v: v)
    lines = [sep.join(header)] if header else []
    lines += [sep.join([r[0]] + [fmt(v) for v in r[1:]]) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("sep,comma,header,zipped", [(";", False, True, False), (" ", True, False, False),
                                                      ("\t", True, True, True), (",", False, True, False)])
def test_layouts_jtsk(tmp_path, sep, comma, header, zipped):
    # RTS-like output: id, input lat/lon, output Y, X rounded to mm, one point off by 3 mm in Y
    rows = []
    for r in EXPECTED:
        y = float(r["jtsk_Y"]) + (0.003 if r["id"] == "RTS07" else 0.0)
        rows.append([r["id"], r["latitude"], r["longitude"], f"{y:.3f}", f"{float(r['jtsk_X']):.3f}"])
    f = _write(tmp_path / "out.txt", rows, sep, comma, ["id", "B", "L", "Y", "X"] if header else None)
    if zipped:
        with zipfile.ZipFile(tmp_path / "out.zip", "w") as z:
            z.write(f, "out.txt")
        f = tmp_path / "out.zip"
    worst = compare_rts.main("jtsk", str(f), out_dir=tmp_path)
    assert 0.0029 < worst < 0.0036
    res = {r["id"]: float(r["distance_mm"]) for r in csv.DictReader(open(tmp_path / "result_jtsk.csv"))}
    assert len(res) == len(EXPECTED) and max(res, key=res.get) == "RTS07"


def test_reverse_and_negative_signs(tmp_path):
    rows = [[r["id"], f"{-float(r['jtsk_Y']):.3f}", f"{-float(r['jtsk_X']):.3f}", f"{float(r['back_latitude']):.9f}",
             f"{float(r['back_longitude']):.9f}"] for r in EXPECTED]
    f = _write(tmp_path / "back.txt", rows, ";", False, ["id", "Y", "X", "lat", "lon"])
    assert compare_rts.main("etrs89", str(f), out_dir=tmp_path) < 0.0001
    rows = [[r["id"], f"{-float(r['jtsk03_Y']):.4f}", f"{-float(r['jtsk03_X']):.4f}"] for r in EXPECTED]
    f = _write(tmp_path / "j03.txt", rows, ";", False, None)
    assert compare_rts.main("jtsk03", str(f), out_dir=tmp_path) < 0.0001


def test_points_are_inside_the_grid_and_spread():
    lat = [float(r["latitude"]) for r in EXPECTED]
    lon = [float(r["longitude"]) for r in EXPECTED]
    assert len(EXPECTED) == 56
    assert min(lon) < 17.0 and max(lon) > 22.3 and min(lat) < 47.9 and max(lat) > 49.4
    shift = [float(r["jtsk03_jtsk_shift_m"]) for r in EXPECTED]
    assert min(shift) < 0.05 and max(shift) > 1.5
