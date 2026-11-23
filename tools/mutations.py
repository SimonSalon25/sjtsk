"""Mutation check: break the code on purpose, one change at a time; the test suite must fail every time.

    python tools/mutations.py            # all mutations
    python tools/mutations.py "portable" # only mutations whose name contains the text
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = "src/sjtsk/"
MUTATIONS = [
    ("WGS 84 not recognised (falls to PROJ's own choice)", P + "crs.py",
     "KNOWN = {5514: JTSK, 102067: JTSK, 8353: JTSK03, 4258: ETRS89, 4326: WGS84}",
     "KNOWN = {5514: JTSK, 102067: JTSK, 8353: JTSK03, 4258: ETRS89}"),
    ("JTSK03 treated as JTSK", P + "transform.py",
     '    if s is _c.JTSK03:\n        return "j03", None', '    if s is _c.JTSK03:\n        return "jtsk", None'),
    ("inverse Helmert = forward parameters negated", P + "variants.py",
     "HELMERT_JTSK03_TO_ETRS89 = dict(x=485.021, y=169.465, z=483.839,",
     "HELMERT_JTSK03_TO_ETRS89 = dict(x=485.014055, y=169.473618, z=483.842943,"),
    ("grid direction reversed", P + "transform.py", "return self._grid(lo, la, TransformDirection.FORWARD)",
     "return self._grid(lo, la, TransformDirection.INVERSE)"),
    ("outside-grid points not counted", P + "transform.py", "            self.outside_grid += n\n", ""),
    ("5513 / 2065 through ETRS89 (no direct conversion)", P + "transform.py",
     "    node = _sjtsk_datum(crs)\n", "    node = None\n"),
    ("LOCAL_CS code taken from the unit", P + "crs.py",
     r"""\s*\]\s*\]\s*$', text.strip())""", r"""\s*\]', text.strip())"""),
    ("control points: negative E/N accepted", P + "control_points.py",
     "if not (150_000 <= y <= 650_000 and 1_100_000 <= x <= 1_400_000):",
     "if not (-650_000 <= y <= 650_000 and 1_100_000 <= x <= 1_400_000):"),
    ("control points: E/N sign", P + "control_points.py", "return -self.y, -self.x", "return self.y, self.x"),
    ("portable: rotation sign", P + "portable.py", "ty + m * (-rz * x + y + rx * z),", "ty + m * (rz * x + y + rx * z),"),
    ("portable: grid row order", P + "portable.py", "fy = (self.lat0 - lat) / self.dlat", "fy = (lat - self.lat0) / self.dlat"),
    ("sk4 with coordinate-frame convention", P + "variants.py",
     'HELMERT_SK4 = dict(x=485.0, y=169.5, z=483.8, rx=7.786, ry=4.398, rz=4.103, s=0.0,\n                   convention="position_vector")',
     'HELMERT_SK4 = dict(x=485.0, y=169.5, z=483.8, rx=7.786, ry=4.398, rz=4.103, s=0.0,\n                   convention="coordinate_frame")'),
]
only = sys.argv[1] if len(sys.argv) > 1 else ""
survived = 0
for name, file, old, new in MUTATIONS:
    if only not in name:
        continue
    d = Path(tempfile.mkdtemp()) / "k"
    shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    p = d / file
    text = p.read_text(encoding="utf-8")
    assert text.count(old) == 1, (name, text.count(old))
    p.write_text(text.replace(old, new), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "tests"], cwd=d,
                       capture_output=True, text=True)
    caught = r.returncode != 0
    survived += not caught
    print(("CAUGHT   " if caught else "SURVIVED ") + name, flush=True)
    shutil.rmtree(d.parent, ignore_errors=True)
sys.exit(1 if survived else 0)
