# Job Intelligence

A local React/Vite research workbench with a FastAPI backend. Personal records and historical private job leads are excluded from this public distribution.

## Data flow
Editable profile → bounded plan → independent connectors → normalization and
deduplication → strict geographic/work-mode constraints → requirement analysis →
multi-factor matching → public evidence checks → ranking → at most 50 results.

FastAPI binds to 127.0.0.1:8765 and serves the production Vite build. SQLite holds
encrypted JSON records for profiles, preferences, jobs, runs and TTL caches.
Windows DPAPI protects the encryption key; POSIX uses a mode-0600 key file.
This protects stored payloads, not a compromised running user account.

## Services
- `models.py`: validated contracts, evidence and uncertainty.
- `profile.py` / `document_worker.py`: local extraction, bounded isolated process.
- `ontology.py`, `matching.py`, `geo.py`: transparent deterministic intelligence.
- `network.py`: public-only pinned DNS, robots, host throttling, retry/circuit logic.
- `connectors.py`: Greenhouse, Lever, Remotive, JSON-LD careers and manual import.
- `verification.py`: source-backed checks, no legitimacy claims from HTTP 200.
- `llm.py`: optional OpenAI-compatible/local structured advisory enrichment.
- `pipeline.py`: persisted runs, incremental results, counters and cancellation.
- `main.py`: local API, request limits, same-origin/session-token protection.

## Deliberate boundaries
LinkedIn is browser-assisted/manual: search URLs and import; it never reads Chrome
cookies or claims an authenticated session. Public APIs can fail independently.
Company-board discovery requires configured board identifiers. Remotive is a
remote-only source with delayed listings, source attribution and a six-hour cache.
Exact office coordinates are required for strict radius admission. City centroids
are not office locations. Distances are straight-line, not commute distances.
Remote eligibility restrictions remain visible and require user confirmation.

LLM is disabled by default. Opt-in sends a minimised skills/experience profile and
job text to the explicitly configured endpoint, never an uploaded CV document.
Model advice is evidence-checked and cannot change deterministic scores or invent
user qualifications. No auto-application, messages, credential collection or
public deployment. Document processing is isolated with resource/time limits;
it is not an OS security sandbox. Scanned PDFs require OCR outside this release.

## Validation
Backend tests cover parsers, ontology, deduplication, geo uncertainty, factor
coverage, ranking, source failure, verification, encryption and API protections.
Frontend has TypeScript/build checks and browser-based workflow/accessibility QA.
