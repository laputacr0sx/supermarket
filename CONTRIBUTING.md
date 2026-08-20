# Git workflow

Solo is fine. `main` still stays green.

## Branch

| Branch | Role |
|---|---|
| `main` | Always shippable. No force-push. |
| `feat/…` `fix/…` `chore/…` `docs/…` `test/…` | Short-lived. One concern. Delete after merge. |

Until a GitHub remote exists, committing on `main` is ok. After the remote exists: branch, PR, merge.

## Commits

Conventional, present tense, one concern:

`feat:` `fix:` `test:` `chore:` `docs:` `ci:`

Never commit `data/`, `*.db`, `.env`, secrets, or full card UIDs.

## Before you push

```
python -m ruff check .
python -m pytest
```

## Pull request

Open a PR even if you will merge it. CI must pass. **Squash merge** to `main`, then delete the branch.

## GitHub settings (once)

Settings → Rules → Ruleset on `main`:

- Block force pushes
- Require a pull request
- Require status check `CI`
- Do **not** require approvals (solo)
