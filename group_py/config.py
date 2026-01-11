"""YAML configuration loader for group-py."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    Load and validate YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Validated configuration dict

    Raises:
        ConfigError: If config is invalid or file not found

    Example YAML:
        api_key: "your_api_key"
        group_id: "your_group_id"
        user_id: "your_user_id"

        realtime:
          enabled: true
          reconnect: true

        bots:
          - name: "System"
            primary: true
          - name: "Bean"
            bot_id: "existing_bot_id"
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with open(path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")

    if config is None:
        raise ConfigError("Config file is empty")

    # Validate required fields
    if not config.get("api_key"):
        raise ConfigError("api_key is required in config")

    if not config.get("group_id"):
        raise ConfigError("group_id is required in config")

    return config


def get_config_value(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Get config value with environment variable fallback.

    Priority: Config file > Environment variable > Default

    Args:
        config: Config dict from YAML
        key: Config key to look up
        default: Default value if not found

    Returns:
        Config value

    Example:
        config = {"api_key": "from_yaml"}

        # Returns value from config
        api_key = get_config_value(config, "api_key")

        # Falls back to environment variable
        bot_name = get_config_value(config, "bot_name")  # Checks GROUPME_BOT_NAME

        # Falls back to default
        timeout = get_config_value(config, "timeout", default=30)
    """
    # Check config dict first
    if key in config:
        return config[key]

    # Check environment variable
    env_key = f"GROUPME_{key.upper()}"
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value

    return default
