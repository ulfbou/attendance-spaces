# Prototype 1 acceptance

Repository readiness requires tested domain invariants, authorization boundaries,
base-path-safe Pages output, deployable deterministic packaging, bounded cost
controls, privacy checks, auditable owner corrections, and direct Excel export
without permanent export storage.

## Issue 3 authentication acceptance

- Public runtime configuration contains no secret.
- Login uses authorization code flow with fresh PKCE S256 and state.
- Callback transactions are exact, age-bounded, and single-use.
- Failure creates no authenticated browser session.
- Callback and logout remain safe beneath `/attendance-spaces/`.
- Browser claims are presentation-only; backend JWT and membership checks remain mandatory.

## Issue 4 backend acceptance

Issue #4 backend details and established invariants remain defined in
`docs/backend-and-data-model.md`. Issue #5 must preserve those boundaries.

## Issue 5 repository gate

- `python scripts/validate.py` passes.
- `python -m unittest discover -s tests` passes.
- Python compilation and deterministic package identity pass.
- The backend template deploys the repository package, defines one budget, and fixes log retention to seven days.
- Non-members and participants cannot cross owner or other-participant boundaries.
- Corrections preserve original evidence inside an immutable audit event.
- Excel export is owner-only, generated in memory, and creates no storage object.

## Live gate

Live acceptance is separate and binds exact commit, tree, package SHA-256, stack,
and region. It consists of five bounded workflows: authentication; owner operations;
participant/privacy; infrastructure and cost inspection; and teardown. Each workflow
records `PASS`, `FAIL`, `NOT_RUN`, or `NOT_APPLICABLE` with bounded evidence. The
owner smoke command covers only owner operations and cannot establish the overall
live gate. The overall conclusion remains `NOT_RUN` until every required workflow
has executable evidence. Static tests never satisfy this gate.
