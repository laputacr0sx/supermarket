# Git workflow

Solo is fine. `main` still stays green.

## Branch

| Branch | Role |
|---|---|
| `main` | Always shippable. No force-push. |
| `feat/…` `fix/…` `chore/…` `docs/…` `test/…` | Short-lived. One concern. Delete after merge. |

Home and work: GitHub is the handoff. Do not copy the folder. Never leave uncommitted work on one PC.

```
git checkout main
git pull --ff-only
```

Unfinished work: commit on `feat/…` and `git push -u origin HEAD`, then pull that branch on the other PC. After the remote exists: branch, PR, merge. Do not commit straight to `main`.

## Commits

Conventional, present tense, one concern:

`feat:` `fix:` `test:` `chore:` `docs:` `ci:`

Never commit `data/`, `*.db`, `.env`, secrets, or full card UIDs.

## Before you push

```
uv sync
uv run ruff check src tests
uv run mypy
uv run pytest
```

## Pull request

Open a PR even if you will merge it. CI must pass. **Squash merge** to `main`, then delete the branch.

## GitHub settings (once)

Settings → Rules → Ruleset on `main`:

- Block force pushes
- Require a pull request
- Require status check `CI`
- Do **not** require approvals (solo)
