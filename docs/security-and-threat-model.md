# Security and threat model

The first prototype enforces authentication, space-local authorization,
non-secret opaque context identifiers, separate invitation tokens, auditable
owner corrections, and strict separation of ManagerNote from
ParticipantComment. GitHub Actions permissions and AWS roles must remain
least-privileged and repository-scoped.
