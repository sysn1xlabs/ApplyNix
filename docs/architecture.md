# Architecture

`core.py` owns profile validation, job analysis, deterministic résumé preparation, source verification, SQLite tracking and exports. `cli.py` orchestrates commands. `web.py` serves a loopback-only HTTP dashboard; `dashboard.html` provides an offline interface without external assets.

Preparation copies the profile, parses job lines, ranks explicitly supplied skills and experience bullets, and records JSON-like dotted source references. Verification reconstructs the complete deterministic bundle to reject ungrounded modifications. Storage hashes the complete bundle and deduplicates identical profile/job snapshots. Different jobs or updated profiles produce separate records.

Approval requires review and the exact application identifier. It marks READY only. The user submits independently and records a receipt note to mark APPLIED. Recruitment outcomes require a recorded application. The events table records preparations, approvals and status changes. Resetting to TAILORED revokes readiness and requires approval again before recording another submission.

Weights: required keyword = 3; preferred or unclassified = 1. Coverage = matched weight / total recognized weight. No recognized skills returns null. Required classification wins over preferred when repeated.

The server listens on 127.0.0.1, validates Host, rejects write requests from other origins, accepts JSON only, and caps request size. It is a single-user local tool, not a multi-user service. Do not expose it through a proxy or bind it publicly.
