"""Host STORE_* env must not leak into tests (any OS, any developer shell)."""

from __future__ import annotations

import os

from store.config import Settings, get_settings


def test_host_store_env_is_replaced_with_memory_db() -> None:
    leaked = [key for key in os.environ if key.startswith("STORE_") and key != "STORE_DATABASE"]
    assert leaked == []
    assert os.environ.get("STORE_DATABASE") == ":memory:"


def test_settings_use_in_memory_defaults() -> None:
    settings = Settings(database=":memory:", docs=True)
    assert settings.database == ":memory:"
    assert settings.learn_on_unknown is True
    assert settings.admin_password == ""
    assert get_settings().database == ":memory:"
