# Validation record

Validated in the build environment on 2026-10-03 with Python 3.12.

- `python -m unittest discover -s tests -v`: 11 tests passed.
- CLI init, tailoring and CSV batch preparation completed with fictional data.
- Requirement weights and missing keywords, unknown vocabulary, substring boundaries, required/preferred precedence and extractive ordering tested.
- Modified claims, résumé content, analysis, profile snapshots and stored bundle data rejected.
- Duplicate preparation, approval-before-application and receipt-note requirement tested.
- HTML injection escaped in résumé exports.
- Local HTTP dashboard served; JSON preparation, exact approval phrase, audit events and cross-origin write rejection tested.

Browser rendering was not visually verified: the available Playwright package had no installed browser executable. The HTTP integration test checks the served dashboard and its API, but does not execute frontend JavaScript or validate layout. CI is configured for Python 3.10, 3.12 and 3.13; those remote runs have not been executed here.

Not validated: employer submissions, AI providers, URL ingestion, DOCX generation or direct PDF generation, which are not implemented in this release.
