# Security and threat model

The first prototype enforces authentication, space-local authorization,
non-secret opaque context identifiers, separate invitation tokens, auditable
owner corrections, and strict separation of ManagerNote from
ParticipantComment. GitHub Actions permissions and AWS roles must remain
least-privileged and repository-scoped.

## Browser authentication boundary
The public client uses Cognito authorization code flow with PKCE S256. Every login
creates fresh cryptographic state and verifier values in session storage. Callback
state is mandatory, single-use, age-bounded, and removed before code exchange.
Authorization codes and tokens are removed from the visible URL and are never logged.

The browser decodes only bounded identity claims for presentation. It does not make
an authorization decision from those claims. The Lambda must independently verify
the Cognito JWT signature, issuer, client, expiration, and token_use, then evaluate
current space-local membership for every protected operation.

Issue #4 backend details are defined in `docs/backend-and-data-model.md`.
