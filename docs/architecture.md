# Architecture

The static frontend is hosted by GitHub Pages beneath `/attendance-spaces/`.
AWS is a bounded execution and identity capability, not the product authority.
The API uses Cognito-issued identity and space-local authorization. Invitation
tokens are random, revocable, outbound tokens and are never space identifiers.

## Authentication flow
The static browser client is a public OAuth client without a client secret. It sends
users to Cognito Hosted UI with authorization code flow, a fresh PKCE S256 challenge,
and an exact callback URL beneath the public base path. Google is selected through
Cognito, so provider tokens do not become application credentials.

The callback consumes its transaction once, exchanges the code at Cognito, keeps a
short browser session in session storage, restores only validated attendance context,
and fails closed. Definitive token verification and space authorization belong to the
backend boundary.
