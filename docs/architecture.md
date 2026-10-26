# Architecture

The static frontend is hosted by GitHub Pages beneath `/attendance-spaces/`.
AWS is a bounded execution and identity capability, not the product authority.
The API uses Cognito-issued identity and space-local authorization. Invitation
tokens are random, revocable, outbound tokens and are never space identifiers.
