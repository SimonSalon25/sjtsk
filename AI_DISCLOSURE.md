# Use of generative AI

This project was developed with a generative AI assistant. We state this openly because the way the work was done
is itself one of the results we want to share (see the planned paper on AI-assisted development in GIS).

## Tools

| tool | where |
|---|---|
| Claude models (Anthropic) in the claude.ai agent workspace, including **Claude Opus 5.5**, for this package (November 2026); the model used in each session was not recorded | code, tests, documentation, this file |
| Claude models in earlier sessions of the parent application *Lesná mapa* (2026; exact model versions per session were not recorded) | the original Slovak implementation from which this package was translated |

## Division of work

**Author (human), Šimon Saloň:**
- defined the problem (the national map that GDAL could not open) and every requirement;
- made the decisions recorded in the project log (e.g. the official ÚGKK transformation as the default with the
  grid included, recompute JTSK03 rasters by the grid instead of treating them as JTSK, one path for WGS 84 and
  ETRS89, MIT licence);
- identified the practical context (cadastral deliveries in S-JTSK, national datasets in JTSK03) and tested the
  applications that use this package on his own data;
- did not review the code line by line. He reviewed its behaviour: he read the decision log and the test descriptions for each change, ran every version on his own national data on his own computer (Windows) and in QGIS, reported failures, and accepted a change only after the full test suite and the mutation check passed. The authors take responsibility for the published code.

**Co-authors (humans):** Milan Koreň, František Chudý, Julián Tomaštík and Miroslav Kardoš (Department of Forest Resource Planning and Informatics, Technical University in Zvolen) work in GIS and forest mapping. In consultations with them the practical problems were identified that this work then solved with the AI assistant.

**AI assistant:**
- wrote the code, the tests and the documentation;
- measured the differences between the transformation variants and analysed what PROJ chooses in which
  installation;
- proposed options for decisions; the author chose.

## How AI output was checked

Nothing is accepted because the AI says it works. Every change in the parent project carries a numbered entry in
a decision log, a test, and a **mutation check**: the fix is deliberately broken and the test must fail. The full
test suite of the parent application (≈ 300 tests) runs before every release. Results on real data are measured
on the author's computer. Known AI mistakes caught by this process are documented in the project log (for example
mis-identified EPSG transformation codes and "caught" mutations that were in fact not caught); they are part of the
material for the paper.
