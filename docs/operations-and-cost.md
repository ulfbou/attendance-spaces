# Operations and cost
Prototype 1 uses Cognito Lite, one Lambda Function URL, one DynamoDB table, seven-day CloudWatch retention, and one monthly AWS Budget. API Gateway, Amplify Hosting, S3 export storage, WAF, CloudFront, and WebSockets remain excluded.

## Prerequisites
AWS CLI credentials, a region, a versioned deployment-artifact bucket, Google OAuth client credentials, a budget notification email, and GitHub repository-variable access are required. The deployment bucket stores code packages only. It must never receive attendance exports.

## Deterministic package and deployment
Run `python scripts/package_backend.py --output dist/backend.zip` twice and compare SHA-256 values before upload. Upload that exact package to the deployment bucket, then deploy `infrastructure/backend.yaml` with `PackageBucket`, `PackageKey`, optional `PackageVersion`, Cognito identifiers, `BudgetAmount`, and `BudgetEmail`. Reusing the same parameters and package identity is an idempotent stack update.

The template owns the Function URL, DynamoDB table, seven-day log group, bounded concurrency, and budget. The Lambda template references the real repository package and contains no inline placeholder.

## Live acceptance
Use `scripts/smoke_test.py` with a real Cognito access token. Tokens are CLI inputs and are never written to evidence. Record commit, tree, package SHA-256, stack, region, secret-free outputs, budget presence, retention, smoke observations, and separate conclusions using `contracts/acceptance-evidence-v1.schema.json`. Static validation is not live acceptance.

## Export and privacy
Excel workbooks are constructed in Lambda memory and returned directly. No export bucket, object write, or retained export resource exists. Participants cannot invoke owner export. Manager notes and participant comments remain distinct columns and authorization boundaries.

## Teardown and recovery
Download required secret-free evidence first. Delete the backend stack, then the Cognito stack after disabling Cognito deletion protection if intentional. Empty and remove the deployment-artifact bucket separately if it is dedicated to this prototype. CloudFormation deletes the prototype table; point-in-time recovery is operational protection, not retention after stack deletion. Confirm the budget, log group, Lambda, URL, table, and Cognito resources are absent. Never delete shared artifact infrastructure.

## Cost expectation
The design favors on-demand DynamoDB, bounded Lambda concurrency, short logs, Cognito Lite, and a configurable low monthly budget. AWS Budgets notifications are delayed signals, not hard spending caps.
