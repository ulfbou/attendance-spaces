# Contracts

These JSON Schemas are the canonical machine-readable Prototype 1 vocabulary.
They use JSON Schema Draft 2020-12 and are versioned independently of deployment.

## Invariants

- A user owns zero or one AttendanceSpace through a unique ownership claim.
- Roles are local to one AttendanceSpace. Prototype roles are OWNER and PARTICIPANT.
- Creating a space atomically creates the space, OWNER membership, unique ownership
  claim, audit event, and idempotency record.
- Attendance facts are persisted separately from derived display states.
- Invitation tokens are random outbound credentials and are never `spaceId` values.
- URL values identify untrusted context only. Authorization is decided server-side
  from authenticated identity and current membership.

Run `python scripts/validate.py` to verify the contract set.
