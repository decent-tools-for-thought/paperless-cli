from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

APP_NAME = "paperless-cli"
DEFAULT_API_VERSION = 9


@dataclass
class Profile:
    name: str
    base_url: str
    token: str
    api_version: int = DEFAULT_API_VERSION
    username: str | None = None


@dataclass
class Config:
    active_profile: str | None
    profiles: dict[str, Profile]


def config_dir() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    if root:
        return Path(root) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


def _normalize_url(value: str) -> str:
    value = value.strip()
    return value[:-1] if value.endswith("/") else value


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        return Config(active_profile=None, profiles={})
    data = json.loads(path.read_text())
    profiles = {
        name: Profile(name=name, **payload) for name, payload in data.get("profiles", {}).items()
    }
    return Config(
        active_profile=data.get("active_profile"),
        profiles=profiles,
    )


def save_config(config: Config) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    profiles = {
        name: {key: value for key, value in asdict(profile).items() if key != "name"}
        for name, profile in config.profiles.items()
    }
    payload = {
        "active_profile": config.active_profile,
        "profiles": profiles,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def get_profile(
    profile_name: str | None = None,
    *,
    explicit_url: str | None = None,
    explicit_token: str | None = None,
    explicit_api_version: int | None = None,
) -> Profile:
    config = load_config()
    if explicit_url and explicit_token:
        return Profile(
            name=profile_name or "adhoc",
            base_url=_normalize_url(explicit_url),
            token=explicit_token,
            api_version=explicit_api_version or DEFAULT_API_VERSION,
        )
    name = profile_name or config.active_profile
    if not name:
        raise SystemExit("No active profile. Run `paperless auth login --url ... --username ...`.")
    try:
        profile = config.profiles[name]
    except KeyError as exc:
        raise SystemExit(f"Unknown profile: {name}") from exc
    if explicit_url:
        profile.base_url = _normalize_url(explicit_url)
    if explicit_token:
        profile.token = explicit_token
    if explicit_api_version:
        profile.api_version = explicit_api_version
    return profile


def upsert_profile(profile: Profile, *, activate: bool = True) -> None:
    config = load_config()
    profile.base_url = _normalize_url(profile.base_url)
    config.profiles[profile.name] = profile
    if activate:
        config.active_profile = profile.name
    save_config(config)


def remove_profile(name: str) -> bool:
    config = load_config()
    removed = config.profiles.pop(name, None) is not None
    if config.active_profile == name:
        config.active_profile = next(iter(config.profiles), None)
    save_config(config)
    return removed


def set_active_profile(name: str) -> None:
    config = load_config()
    if name not in config.profiles:
        raise SystemExit(f"Unknown profile: {name}")
    config.active_profile = name
    save_config(config)
