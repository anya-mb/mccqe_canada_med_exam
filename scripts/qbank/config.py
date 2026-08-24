"""Project configuration loading and validation."""

from pathlib import Path

from .errors import ConfigError
from .jsonio import read_json

_RESEARCH_MODES = {"CODEX_NATIVE", "MANUAL_RESEARCH", "API_AUTOMATED"}


def _merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(root: Path) -> dict:
    """Load committed project config and recursively apply its local override."""
    root = Path(root)
    committed_path = root / "config" / "project.json"
    local_path = root / "config" / "project.local.json"
    try:
        config = read_json(committed_path)
    except (OSError, ValueError, TypeError) as exc:
        raise ConfigError(f"unable to read project configuration: {committed_path}") from exc
    if not isinstance(config, dict):
        raise ConfigError("project configuration must be a JSON object")

    if local_path.is_file():
        try:
            local = read_json(local_path)
        except (OSError, ValueError, TypeError) as exc:
            raise ConfigError(f"unable to read local configuration: {local_path}") from exc
        if not isinstance(local, dict):
            raise ConfigError("local project configuration must be a JSON object")
        config = _merge(config, local)

    mode = config.get("research_mode")
    if mode not in _RESEARCH_MODES:
        raise ConfigError(f"unsupported research_mode: {mode!r}")
    if mode == "API_AUTOMATED" and config.get("api_automated_enabled") is not True:
        raise ConfigError("api_automated_enabled must be exactly true for API_AUTOMATED")
    return config
