"""Host STORE_* env must not leak into tests (any OS, any developer shell)."""

from __future__ import annotations

import os

from store.config import Settings


def test_store_env_is_cleared_for_tests() -> None:
    leaked = [key for key in os.environ if key.startswith("STORE_")]
    assert leaked == []


def test_settings_use_in_memory_defaults() -> None:
    settings = Settings(database=":memory:", docs=True)
    assert settings.database == ":memory:"
    assert settings.learn_on_unknown is True
    assert settings.admin_password == ""
