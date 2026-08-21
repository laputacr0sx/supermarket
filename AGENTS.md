# store

Checks: `uv run ruff check src tests`, `uv run mypy`, `uv run pytest`.

## Types

Annotate every class field and every function/method (parameters and return). Parameterize `dict`, `list`, and `tuple`. HTTP JSON is a Pydantic `BaseModel` in `store.api.schemas`. ORM tables stay SQLAlchemy `Mapped[]`. The kiosk FSM stays frozen dataclasses.

Skip a type only when the user says so. Then `# type: ignore[<code>]` or `# noqa: ANN…` on that line, with the reason.

`uv run mypy` covers `src/store` and `tests`. `prototypes/` and `alembic/` are outside the target.
