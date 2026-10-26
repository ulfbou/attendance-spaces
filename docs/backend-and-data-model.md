# Backend and data model

Prototype 1 uses one Lambda Function URL and one DynamoDB table. `PK` and `SK` encode bounded aggregates. Space creation is a five-write DynamoDB transaction: space, OWNER membership, unique per-user ownership claim, audit event, and durable idempotency result. A failed condition cancels the complete transaction.

Every protected route requires a Cognito bearer token and current space membership. URL identifiers select resources but never grant access. Owners receive aggregate space data; participants receive only their own attendance facts with owner-managed checkpoints. Stored facts remain separate from derived display states.

The deployed token-verifier adapter must verify signature, issuer, client, expiry, and `token_use` before `sub` is accepted. Function URL IAM authentication is intentionally `NONE` because Cognito JWT authentication occurs in the application boundary; CORS is restricted to the Pages origin and is not authorization.
