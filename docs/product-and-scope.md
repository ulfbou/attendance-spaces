# Product and scope

An authenticated user may own zero or one AttendanceSpace and participate in
any number of other spaces. Prototype roles are OWNER and PARTICIPANT; MANAGER
is reserved for later.

Creating an AttendanceSpace must atomically create the space, OWNER membership,
a unique ownership claim, an audit event, and idempotency protection.

Checkpoint kinds are CHECK_IN, PRESENCE_CHECK, and CHECK_OUT. Lifecycle states
are DRAFT, SCHEDULED, OPEN, CLOSED, and CANCELLED. Attendance facts are stored
separately from derived display states such as UPCOMING, AVAILABLE, COMPLETED,
ABSENT, MISSED, and CANCELLED.
