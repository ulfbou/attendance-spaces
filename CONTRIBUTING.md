# Contributing

`master` is the controlling branch. After the bootstrap commit, changes reach
`master` through reviewed pull requests.

## Required workflow

1. Create an issue with a bounded outcome.
2. Create a focused branch from current `master`.
3. Keep product, infrastructure, documentation, and tests aligned.
4. Run `python scripts/validate.py`.
5. Open a pull request linked to the issue and Prototype 1 milestone.
6. Merge only after required checks pass.

Do not commit secrets, identity-provider credentials, exported attendance data,
or live participant data.
