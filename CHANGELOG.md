# Changelog

## 0.1.1 — 2026-11-24
Documentation and testing only; the transformations are unchanged.
- The 12 points of the QGIS test are called test points, not control points: their expected values come from this
  package, so they show what QGIS does relative to the EPSG definition, not accuracy (METHODOLOGY section 3).
- Figures on 3,978 points are described as computed (a model comparison), not measured.
- QGIS 3.44's default operation (Czech parameters) is up to 4.2 m off (mean 1.9 m) on the 3,978 points; the earlier
  "0.5–3.6 m" came from 12 test points only and understated the error.
- Independent check against the binding RTS service (METHODOLOGY 5.1, 24 November 2026, 56 points): grid step
  agrees to the rounding of the RTS output; the Helmert step differs by a constant 5.3 mm (max 6.0 mm); QGIS 3.44's
  default is 1.91 m off RTS on average, up to 4.10 m. RTS outputs stored in `validation/rts/`, guarded by
  `tests/test_rts_agreement.py`.
- Legal reference made precise: regulation 300/2009 Coll., § 18(1) (JTSK for the cadastre) and § 2(10) (RTS binding).
- Install from GitHub (not on PyPI yet); tests run on GitHub Actions (Linux, Windows; Python 3.10, 3.13).
- AI_DISCLOSURE: the model used in each session was not recorded.

## 0.1.0 — 2026-11-22
First public version, translated from the Slovak module `lesna_jadro.suradnice` 0.2.0 of the Lesná mapa
applications: official ÚGKK chain with the GKÚ grid, variants sk3/sk4/proj_auto, other S-JTSK notations
(5513, 2065, 8352) without datum shift, control points, portable pure-Python implementation. 23 tests, 12 mutations
caught.
