"""Catalogue of coordinate reference systems and recognising them from any notation.

Two realizations of S-JTSK are distinguished: JTSK (EPSG:5514) and JTSK03 (EPSG:8353). According to the GKÚ
grid they differ by 0.69 m on average and up to 1.64 m in Slovakia — they are not interchangeable.

A raster written as `LOCAL_CS[... AUTHORITY["EPSG","8353"]]` (common for national elevation models) carries the
code although PROJ cannot build a transformation from it; the code is therefore also extracted from such WKT.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Crs:
    code: str            # short name in this package
    epsg: int
    name: str
    realization: str | None = None   # "JTSK" / "JTSK03" for S-JTSK, else None

    @property
    def epsg_text(self) -> str:
        return f"EPSG:{self.epsg}"

    def __str__(self) -> str:
        return f"{self.name} ({self.epsg_text})"


JTSK = Crs("JTSK", 5514, "S-JTSK / Krovak East North", "JTSK")
JTSK03 = Crs("JTSK03", 8353, "S-JTSK [JTSK03] / Krovak East North", "JTSK03")
ETRS89 = Crs("ETRS89", 4258, "ETRS89")
WGS84 = Crs("WGS84", 4326, "WGS 84")

#: EPSG (and ESRI) codes that mean exactly these systems — same axes and realization.
#: EPSG:5513 (S-JTSK / Krovak, positive south/west axes) is NOT here: different axes (handled as another
#: notation of the same datum by the transformer, without any datum shift).
KNOWN = {5514: JTSK, 102067: JTSK, 8353: JTSK03, 4258: ETRS89, 4326: WGS84}


def epsg_from(value) -> str | None:
    """EPSG code from `"EPSG:5514"`, a number, WKT (also `LOCAL_CS`), or a pyproj/rasterio CRS object.

    In WKT the code of the system is the AUTHORITY/ID at the very end; nested ones belong to units, ellipsoids…
    """
    if value is None:
        return None
    if isinstance(value, Crs):
        return str(value.epsg)
    if isinstance(value, int):
        return str(value)
    to_epsg = getattr(value, "to_epsg", None)
    if callable(to_epsg):
        try:
            code = to_epsg()
            if code:
                return str(code)
        except Exception:  # noqa: BLE001 — some CRS objects cannot do to_epsg
            pass
        to_wkt = getattr(value, "to_wkt", None)
        value = to_wkt() if callable(to_wkt) else str(value)
    text = str(value)
    direct = re.fullmatch(r"\s*(?:EPSG|ESRI):(\d+)\s*", text, re.IGNORECASE)
    if direct:
        return direct.group(1)
    # The code of the system is the top-level AUTHORITY/ID right before the last bracket. If it is missing
    # (GeoTIFF drops AUTHORITY from LOCAL_CS), the last AUTHORITY in the text belongs to the unit (9001).
    at_end = re.search(r'(?:AUTHORITY|ID)\s*\[\s*"(?:EPSG|ESRI)"\s*,\s*"?(\d+)"?\s*\]\s*\]\s*$', text.strip())
    return at_end.group(1) if at_end else None


def is_unusable(value) -> bool:
    """A notation from which PROJ cannot build a transformation: empty, or `LOCAL_CS` (no datum)."""
    if value is None:
        return True
    to_wkt = getattr(value, "to_wkt", None)
    text = (to_wkt() if callable(to_wkt) else str(value)).strip()
    if not text:
        return True
    return "LOCAL_CS" in text.upper()


def identify(value) -> Crs | None:
    """The catalogue system, or None (another system or an unknown notation)."""
    if isinstance(value, Crs):
        return value
    code = epsg_from(value)
    if code is None:
        return None
    try:
        return KNOWN.get(int(code))
    except ValueError:
        return None
