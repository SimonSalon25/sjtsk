# Check against the official RTS service

The independent check of METHODOLOGY.md, section 5.1: 56 points over Slovakia transformed by the departmental
transformation service of ÚGKK (RTS, https://zbgis.skgeodesy.sk/rts/sk/Transform) and compared with this package.
The points and the expected values are written by `python tools/make_rts_points.py`.

| run | RTS input file | input system | output system | compare with |
|---|---|---|---|---|
| 1 | `rts_input_etrs89.zip` | ETRS89-LatLon [EPSG:4258], form `dd,ddddddddd`, ϕ = column 2, λ = column 3 | S-JTSK (JTSK03) [EPSG:8352] | `python tools/compare_rts.py jtsk03 <output>` |
| 2 | `rts_input_etrs89.zip` | the same | S-JTSK (JTSK) [EPSG:5513] | `python tools/compare_rts.py jtsk <output>` |
| 3 | `rts_input_jtsk.zip` | S-JTSK (JTSK) [EPSG:5513], Y = column 2, X = column 3 | ETRS89-LatLon [EPSG:4258] | `python tools/compare_rts.py etrs89 <output>` |

Settings in RTS for all runs: input format TXT/CSV; column separator *Bodkočiarka* (semicolon); decimal separator
*Bodka* (point); *Súbor obsahuje hlavičku* (the file has a header) ticked; heights: *Bez transformácie výšky* (no
height transformation; the points have no height — the plane result is that of h = 0, as in this package).

Keep the RTS output files unchanged in this folder as `rts_output_1_jtsk03.*`, `rts_output_2_jtsk.*`,
`rts_output_3_etrs89.*`, with the date of the run and the RTS version shown in the page footer in
`rts_runs.txt`. The comparison writes `result_jtsk03.csv`, `result_jtsk.csv` and `result_etrs89.csv`.

**Result (24 November 2026):** see METHODOLOGY.md, section 5.1 — grid step equal to RTS within the rounding of its
output; Helmert step a constant 5.3 mm off (max 6.0 mm); QGIS 3.44's default 1.91 m off RTS on average, up to 4.10 m.

What the result means: agreement within the rounding of the RTS output (about 1 mm) shows that this package
reproduces the binding service on these points; it says nothing about the accuracy of the official transformation
itself with respect to the physical points of the network (that needs identical points, section 5).
`expected.csv` also holds what QGIS 3.44's default operation gives, so run 2 shows its error with respect to RTS.
