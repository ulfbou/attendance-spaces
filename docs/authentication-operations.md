# Authentication operations

## Authority and secret boundary

`infrastructure/cognito.yaml` defines the Prototype 1 Cognito Lite user pool,
public browser client, Cognito domain, and Google federation. The browser client
has no client secret. The Google client secret is a deployment input marked
`NoEcho`; it must not be committed, written to frontend assets, or exposed as a
GitHub Pages variable.

## Google prerequisite

Create a Google Web application OAuth client. Configure the Cognito domain as an
authorized JavaScript origin and the stack output `GoogleRedirectUri` as the
Google authorized redirect URI. Store the displayed Google client secret outside
the repository and supply it only to the CloudFormation deployment.

## Public Pages configuration

After deploying the stack, configure these GitHub repository variables from the
stack outputs:

- `COGNITO_REGION`
- `COGNITO_USER_POOL_ID`
- `COGNITO_CLIENT_ID`
- `COGNITO_DOMAIN`

The Pages workflow renders `frontend/assets/runtime-config.js` only inside the
build job. These values identify public OAuth resources and are not credentials.
The workflow must fail rather than deploy an unauthenticated or partially
configured build when any value is absent.

For local validation, render the same file with:

```bash
python scripts/render_runtime_config.py \
  --region "$COGNITO_REGION" \
  --user-pool-id "$COGNITO_USER_POOL_ID" \
  --client-id "$COGNITO_CLIENT_ID" \
  --domain "$COGNITO_DOMAIN"
```

Do not commit the rendered environment-specific values. Restore the tracked blank
configuration before committing.

## Failure and recovery

A failed, expired, unsolicited, or state-mismatched callback clears all browser
authentication state and presents a safe route to the application. Logout clears
local state even if the Cognito redirect cannot be completed. Browser claims are
presentation-only; the backend remains responsible for JWT and membership checks.
