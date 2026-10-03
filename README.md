# ApplyNix

**Tailor. Review. Apply. Track.**  
An application preparation workspace by **sysn1xlabs**.

ApplyNix v0.1 is a working, offline Python MVP. Paste a job description and supply a factual career profile to prepare a reordered résumé, inspect keyword gaps and claim evidence, approve the exact draft, and track manually submitted applications.

## Quick start

Requires Python 3.10 or newer. No runtime dependencies or API key required.

Extract the ZIP, open a terminal in the `ApplyNix` folder, then run:

```sh
python -m applynix init
python -m applynix serve
```

Open **http://127.0.0.1:8765**. Use **Load fictional example** to try the workflow, or paste your own JSON profile and job description. The dashboard does not store browser form inputs; prepared drafts are saved locally. Replace example profile data before producing real applications.

Optional installation for the shorter command:

```sh
python -m pip install -e .
applynix serve
```

On Windows, use `py` in place of `python` if needed.

## CLI workflow

```sh
python -m applynix analyze examples/sample-job.txt
python -m applynix tailor examples/sample-job.txt
python -m applynix history
python -m applynix show APPLICATION_ID
python -m applynix approve APPLICATION_ID
python -m applynix status APPLICATION_ID APPLIED --note "Submitted manually; confirmation received"
python -m applynix status APPLICATION_ID INTERVIEW --note "Interview invitation received"
python -m applynix batch examples/jobs.csv
```

Replace `APPLICATION_ID` with the ID printed by `tailor`. `approve` displays the résumé, analysis and changes and requires the exact approval phrase. Approval only marks READY. APPLIED requires READY and a user-supplied receipt note; it does not claim to independently verify the employer's receipt.

Use `--profile path/to/profile.json` on analyze/tailor/batch. Global `--home DIRECTORY` selects a workspace. Default: `~/.applynix`, overridable by `APPLYNIX_HOME`.

Exports are saved in `~/.applynix/applications/ID/`:

- `resume.md` — exact supplied facts, reordered for relevance
- `resume.html` — simple single-column, print-friendly résumé; open and use Print → Save as PDF
- `review.json` — analysis, changes, claims, source pointers and snapshots
- `job-description.txt` — original job description

## What works

- Required/preferred/unknown skill classification using a fixed vocabulary
- Transparent weighted keyword coverage and missing-skill list
- Payment, unpaid-role, eligibility and experience review indicators
- Reordering skills and experience bullets without changing factual wording
- Source reference for every rendered résumé claim
- Deterministic source verification, draft digest and duplicate preparation detection
- Local dashboard with résumé, changes, evidence and audit history
- Explicit per-draft approval, SQLite history and outcome tracking
- Batch preparation of up to 50 job description files
- Escaped HTML export, loopback-only dashboard and cross-origin write rejection

## Current limits

This release uses deterministic extraction and ranking, **not an LLM**. It does not fetch URLs, discover jobs, log in, fill employer forms, submit applications, generate cover letters, or export DOCX/direct PDF. No external network calls occur during normal use.

Coverage reflects recognized skill keywords only, not overall qualification, an ATS score or hiring probability. The parser does not reliably understand negation, proficiency, mandatory certifications, skill equivalence, or years of experience. Check every requirement against the original job description. Skills must be explicitly listed in the profile's `skills` array to count as matched. No inference is made from experience text.

Profiles are JSON. Education and certification entries are strings. Experience entries use `company`, `title`, optional `dates`, and `bullets`. Projects are reserved for a later release and are not rendered. Contact fields are copied from the profile; their accuracy is the user's responsibility.

Integrity checks detect inconsistent drafts and accidental changes; they are not cryptographic protection against an attacker who can rewrite both the database and code. Private profiles, snapshots, history and exports are stored unencrypted on the local filesystem. Use disk encryption and protect the workspace.

## Development

```sh
python -m unittest discover -s tests -v
```

See [architecture](docs/architecture.md), [validation](docs/validation.md), [privacy](docs/privacy.md), and [roadmap](ROADMAP.md). MIT licensed.
