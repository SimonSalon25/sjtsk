"""Compare the output of the official RTS service with this package (METHODOLOGY.md, section 5.1).

    python tools/compare_rts.py jtsk03  <RTS output: run 1, ETRS89 → S-JTSK (JTSK03) [EPSG:8352]>
    python tools/compare_rts.py jtsk    <RTS output: run 2, ETRS89 → S-JTSK (JTSK) [EPSG:5513]>
    python tools/compare_rts.py etrs89  <RTS output: run 3, S-JTSK (JTSK) [EPSG:5513] → ETRS89-LatLon>

The RTS output may be a .zip or a text file; the separator (; , tab, space), the decimal mark (point or comma)
and a header row are detected. Points are matched by id (RTS01 … RTS56); the coordinate columns are recognised
by their values (Y 150–700 km, X 1.1–1.4 thousand km, latitude 47–50°, longitude 16–23°; signs ignored), so extra
columns that RTS copies from the input do no harm. Expected values: validation/rts/expected.csv
(tools/make_rts_points.py). Writes validation/rts/result_<kind>.csv and prints the statistics; for jtsk it also
shows how far QGIS 3.44's default operation is from RTS.
"""
import csv
import io
import math
import re
import sys
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # a Windows console (cp1252) cannot print → or – and would fail
    sys.stdout.reconfigure(errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "validation" / "rts"
M_PER_DEG_LAT = 111_200.0


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith((".txt", ".csv"))] or z.namelist()
            data = z.read(names[0])
    else:
        data = path.read_bytes()
    for enc in ("utf-8-sig", "cp1250", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("cannot decode the file")


def split(line: str) -> list[str]:
    if ";" in line:
        return line.split(";")
    if "\t" in line:
        return line.split("\t")
    if "," in line and "." in line:
        return line.split(",")
    if "," in line and len(line.split()) > 1:      # space-separated with a decimal comma
        return line.split()
    if "," in line:
        return line.split(",")
    return line.split()


def number(cell: str):
    c = cell.strip().replace(" ", "")
    if re.fullmatch(r"-?\d+,\d+", c):
        c = c.replace(",", ".")
    try:
        return float(c)
    except ValueError:
        return None


def parse(text: str) -> dict[str, list[float]]:
    """id → numeric cells of the row (in order)."""
    rows = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        cells = split(line)
        ident = next((c for c in cells if re.fullmatch(r"RTS\d{2}", c.strip().strip('"'))), None)
        if ident is None:
            continue
        nums = [v for c in cells if (v := number(c.strip('"'))) is not None]
        rows[ident.strip().strip('"')] = nums
    return rows


def pick(nums, kind):
    vals = [abs(v) for v in nums]
    if kind in ("jtsk03", "jtsk"):
        y = [v for v in vals if 150_000 <= v <= 700_000]
        x = [v for v in vals if 1_100_000 <= v <= 1_400_000]
        if not y or not x:
            raise ValueError(f"no Y/X in {nums}")
        return y[-1], x[-1]              # the last ones: RTS output follows the input columns
    lat = [v for v in vals if 47.0 <= v <= 50.0]
    lon = [v for v in vals if 16.0 <= v <= 23.0]
    if not lat or not lon:
        raise ValueError(f"no latitude/longitude in {nums}")
    return lat[-1], lon[-1]


def stats(d):
    d = sorted(d)
    n = len(d)
    rms = math.sqrt(sum(v * v for v in d) / n)
    p95 = d[min(n - 1, math.ceil(0.95 * n) - 1)]
    return f"n = {n}, mean {sum(d) / n * 1000:.2f} mm, RMS {rms * 1000:.2f} mm, P95 {p95 * 1000:.2f} mm, " \
           f"max {d[-1] * 1000:.2f} mm"


def main(kind: str, path: str, tolerance_m: float = 0.001, out_dir: Path = DIR):
    if kind not in ("jtsk03", "jtsk", "etrs89"):
        sys.exit("kind must be jtsk03, jtsk or etrs89")
    expected = {r["id"]: r for r in csv.DictReader(open(DIR / "expected.csv", encoding="utf-8"))}
    got = parse(read_text(Path(path)))
    missing = sorted(set(expected) - set(got))
    out_rows, dist, qgis = [], [], []
    for ident in sorted(set(expected) & set(got)):
        e = expected[ident]
        a, b = pick(got[ident], kind)
        if kind in ("jtsk03", "jtsk"):
            ey, ex = float(e[f"{kind}_Y"]), float(e[f"{kind}_X"])
            dy, dx = a - ey, b - ex
            row = [ident, f"{a:.4f}", f"{b:.4f}", f"{ey:.4f}", f"{ex:.4f}", f"{dy * 1000:.2f}", f"{dx * 1000:.2f}"]
            if kind == "jtsk" and e.get("qgis344_default_jtsk_Y"):
                q = math.hypot(float(e["qgis344_default_jtsk_Y"]) - a, float(e["qgis344_default_jtsk_X"]) - b)
                qgis.append(q)
                row.append(f"{q:.4f}")
        else:
            elat, elon = float(e["back_latitude"]), float(e["back_longitude"])
            dy = (a - elat) * M_PER_DEG_LAT
            dx = (b - elon) * M_PER_DEG_LAT * math.cos(math.radians(elat))
            row = [ident, f"{a:.10f}", f"{b:.10f}", f"{elat:.10f}", f"{elon:.10f}", f"{dy * 1000:.2f}",
                   f"{dx * 1000:.2f}"]
        d = math.hypot(dy, dx)
        dist.append(d)
        out_rows.append(row + [f"{d * 1000:.2f}"])
    if not out_rows:
        sys.exit("no point of the RTS file matched RTS01 … RTS56 — is it the right file?")
    head = {"jtsk03": ["id", "rts_Y", "rts_X", "sjtsk_Y", "sjtsk_X", "dY_mm", "dX_mm"],
            "jtsk": ["id", "rts_Y", "rts_X", "sjtsk_Y", "sjtsk_X", "dY_mm", "dX_mm"],
            "etrs89": ["id", "rts_lat", "rts_lon", "sjtsk_lat", "sjtsk_lon", "dN_mm", "dE_mm"]}[kind]
    if qgis:
        head.append("qgis344_default_vs_rts_m")
    head.append("distance_mm")
    target = Path(out_dir) / f"result_{kind}.csv"
    with open(target, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(out_rows)
    print(f"{kind}: RTS vs sjtsk (variant ugkk) — {stats(dist)}")
    if missing:
        print(f"missing in the RTS file: {', '.join(missing)}")
    if qgis:
        print(f"QGIS 3.44 default vs RTS: mean {sum(qgis) / len(qgis):.2f} m, max {max(qgis):.2f} m")
    worst = max(dist)
    verdict = "AGREES" if worst <= tolerance_m and not missing else "CHECK"
    print(f"{verdict}: largest difference {worst * 1000:.2f} mm (tolerance {tolerance_m * 1000:.1f} mm, set by the "
          f"number of decimals RTS writes) → {target}")
    return worst


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.001)
