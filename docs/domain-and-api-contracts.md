# Domain and API contracts

## Authority

Files under `contracts/` are the canonical machine-readable Prototype 1 contract.
This document explains their meaning but does not override them.

## Identity and authorization

Identifiers are opaque and namespaced. A URL may carry `space`, `checkpoint`, or
`invite`, but possession of a URL never grants access. The backend authenticates
the caller and evaluates current space-local membership for every protected action.
Invitation tokens are independently generated, revocable, and never derived from a
space identifier.

## Space creation transaction

`CreateAttendanceSpace` is one atomic transaction. It succeeds only when all five
records can be established together: AttendanceSpace, OWNER membership, unique
user ownership claim, audit event, and idempotency record. A repeated accepted
idempotency key returns the established result and must not create another space.
A conflicting ownership claim rejects the complete transaction.

## Checkpoints and attendance

Checkpoint kind and lifecycle are separate dimensions. CHECK_IN, PRESENCE_CHECK,
and CHECK_OUT describe purpose. DRAFT, SCHEDULED, OPEN, CLOSED, and CANCELLED
describe lifecycle. Stored attendance facts record what occurred. UPCOMING,
AVAILABLE, COMPLETED, ABSENT, MISSED, and CANCELLED are derived display states and
must not replace source facts.

## Versioning

Breaking contract changes require a new schema filename and identifier. Additive
changes must still preserve `additionalProperties` policy and consumer validation.
