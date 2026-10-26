# Prototype 1 acceptance

Acceptance requires tested domain invariants, authorization boundaries,
base-path-safe Pages output, deployable infrastructure, bounded cost controls,
privacy documentation, auditable owner corrections, and direct Excel export
without permanent export storage.

## Issue 3 authentication acceptance
- Public runtime configuration contains no secret.
- Login uses authorization code flow with fresh PKCE S256 and state.
- Callback transactions are exact, age-bounded, and single-use.
- Failure creates no authenticated browser session.
- Callback and logout remain safe beneath `/attendance-spaces/`.
- Browser claims are presentation-only; backend JWT and membership checks remain mandatory.
