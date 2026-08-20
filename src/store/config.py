"""Settings. Env wins. Same code on Windows and the LIFEBOOK."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TOML = _REPO_ROOT / "config" / "default.toml"


def default_database_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "store" / "store.db"
    return Path("/var/lib/store/store.db")


def _toml_overlay() -> dict:
    path = Path(os.environ.get("STORE_CONFIG", _DEFAULT_TOML))
    if not path.is_file():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    flat: dict = {}
    if "paths" in data and data["paths"].get("database"):
        flat["database"] = data["paths"]["database"]
    if "net" in data:
        net = data["net"]
        for key in ("pos_host", "pos_port", "admin_host", "admin_port", "docs"):
            if key in net:
                flat[key] = net[key]
    if "catalog" in data:
        for key, val in data["catalog"].items():
            flat[key] = val
    if "play" in data and "uid_debounce_s" in data["play"]:
        flat["uid_debounce_s"] = data["play"]["uid_debounce_s"]
    if "store" in data and "name" in data["store"]:
        flat["store_name"] = data["store"]["name"]
    return flat


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STORE_", extra="ignore")

    store_name: str = "士多"
    database: str = Field(default_factory=lambda: str(default_database_path()))
    docs: bool = False
    pos_host: str = "127.0.0.1"
    pos_port: int = 8787
    admin_host: str = "127.0.0.1"
    admin_port: int = 8788
    learn_on_unknown: bool = True
    store_prefix_min: int = 200
    store_prefix_max: int = 299
    uid_debounce_s: float = 2.0
    staff_pin: str = "0000"


_ENV_FOR_FIELD = {
    "store_name": "STORE_STORE_NAME",
    "database": "STORE_DATABASE",
    "docs": "STORE_DOCS",
    "pos_host": "STORE_POS_HOST",
    "pos_port": "STORE_POS_PORT",
    "admin_host": "STORE_ADMIN_HOST",
    "admin_port": "STORE_ADMIN_PORT",
    "learn_on_unknown": "STORE_LEARN_ON_UNKNOWN",
    "store_prefix_min": "STORE_STORE_PREFIX_MIN",
    "store_prefix_max": "STORE_STORE_PREFIX_MAX",
    "uid_debounce_s": "STORE_UID_DEBOUNCE_S",
    "staff_pin": "STORE_STAFF_PIN",
}


def get_settings() -> Settings:
    overlay = _toml_overlay()
    for field, env_name in _ENV_FOR_FIELD.items():
        if os.environ.get(env_name) is not None:
            overlay.pop(field, None)
    return Settings(**overlay)
