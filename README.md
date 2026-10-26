# Attendance Spaces

A low-cost attendance application with federated identity, space-scoped roles,
and bounded serverless AWS infrastructure.

## Product boundary

This repository owns the Attendance application, domain contracts, frontend,
backend, infrastructure, tests, security documentation, and acceptance evidence.
The `ulfbou.github.io` repository remains the portfolio and discovery authority.

## Prototype architecture

- Static, base-path-safe frontend published at `/attendance-spaces/`
- Amazon Cognito authorization code flow with PKCE; Google is the first provider
- One AWS Lambda exposed through a Function URL
- One Amazon DynamoDB table
- Short CloudWatch retention and AWS Budgets cost controls
- No API Gateway, Amplify Hosting, S3 export storage, WAF, CloudFront, or WebSockets

## Repository layout

- `frontend/` static application source
- `backend/` Lambda application and domain logic
- `infrastructure/` infrastructure as code
- `contracts/` API and data contracts
- `docs/` architecture, privacy, security, operations, and acceptance
- `tests/` cross-boundary tests

Authentication deployment and public configuration are documented in
`docs/authentication-operations.md`.

## Public locations

- Application: <https://ulfbou.github.io/attendance-spaces/>
- Portfolio entry: <https://ulfbou.github.io/projects/attendance-spaces/>

## Current state

Sprint 0 bootstrap. Product behavior and cloud resources are intentionally not
implemented by this commit.
