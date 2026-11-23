"""Named variants of the S-JTSK (JTSK) ↔ ETRS89 transformation.

Why named: PROJ picks "the best available" operation depending on the installation (grid present or not,
network access, version). In the application this package comes from, ETRS89 therefore went through variant (3)
and WGS 84 through variant (4) — the same point had two positions up to 1.36 m apart. Here the variant is always
explicit and its parameters are in the code.

Parameters are copied from the EPSG dataset (PROJ 9.8.1); operation codes in `epsg`.
Differences from the official chain on 3,978 points covering Slovakia (METHODOLOGY.md):
  ugkk 0 · sk3 mean 0.31 / max 1.12 m · sk4 0.68 / 1.69 m.
"""
from __future__ import annotations

from dataclasses import dataclass

#: ETRS89 to S-JTSK [JTSK03] (1), EPSG:8365; ÚGKK, accuracy 1 mm.
HELMERT_ETRS89_TO_JTSK03 = dict(x=-485.014055, y=-169.473618, z=-483.842943,
                                rx=7.78625453, ry=4.39770887, rz=4.10248899, s=0.0,
                                convention="coordinate_frame")
#: S-JTSK [JTSK03] to ETRS89 (1), EPSG:8367; ÚGKK publishes both directions separately, accuracy 1 mm.
HELMERT_JTSK03_TO_ETRS89 = dict(x=485.021, y=169.465, z=483.839,
                                rx=-7.786342, ry=-4.397554, rz=-4.102655, s=0.0,
                                convention="coordinate_frame")
#: S-JTSK to ETRS89 (4), EPSG:4827 (= S-JTSK to WGS 84 (4), EPSG:4836); the JTSK03 key applied directly to JTSK.
HELMERT_SK4 = dict(x=485.0, y=169.5, z=483.8, rx=7.786, ry=4.398, rz=4.103, s=0.0,
                   convention="position_vector")
#: S-JTSK to ETRS89 (3), EPSG:4829, Molodensky-Badekas.
MB_SK3 = dict(x=558.7, y=68.8, z=452.2, rx=-8.025, ry=-4.105, rz=-4.295, s=5.74,
              px=3977358.114, py=1407223.203, pz=4765441.589, convention="coordinate_frame")

GRID = "sk_gku_JTSK03_to_JTSK.tif"   # EPSG:8364 S-JTSK [JTSK03] to S-JTSK (1), GKÚ, CC BY 4.0


@dataclass(frozen=True)
class Variant:
    name: str
    description: str
    epsg: tuple                # EPSG operation codes it consists of (empty = not in EPSG)
    accuracy_m: float | None   # accuracy declared by EPSG (None = not stated)
    grid: bool = False


VARIANTS: dict[str, Variant] = {
    "ugkk": Variant(
        "ugkk", "official ÚGKK chain (EPSG 'ETRS89 to S-JTSK (5)' / 'S-JTSK to ETRS89 (6)'): ETRS89 ↔ JTSK03 "
        "(Helmert, each direction as published by ÚGKK) + JTSK03 ↔ JTSK (GKÚ grid)",
        ("EPSG:8442", "EPSG:8443", "EPSG:8365", "EPSG:8367", "EPSG:8364"), 0.06, grid=True),
    "sk3": Variant("sk3", "S-JTSK to ETRS89 (3), Molodensky-Badekas — PROJ's choice for ETRS89 without the grid",
                   ("EPSG:4829",), 0.5),
    "sk4": Variant("sk4", "S-JTSK to ETRS89/WGS 84 (4), 7-parameter Helmert — PROJ's choice for WGS 84; "
                   "the usual TOWGS84", ("EPSG:4827", "EPSG:4836"), 1.0),
    "proj_auto": Variant("proj_auto", "whatever PROJ picks in this installation — for comparison only", (), None),
}

DEFAULT_VARIANT = "ugkk"


def variant(name: str) -> Variant:
    try:
        return VARIANTS[name]
    except KeyError:
        raise ValueError(f"unknown transformation variant {name!r}; known: {', '.join(VARIANTS)}") from None
