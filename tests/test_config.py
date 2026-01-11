"""Tests for YAML configuration."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from group_py.config import load_yaml_config, get_config_value, ConfigError
from group_py.bot import GroupMeBotManager
from group_py.exceptions import ConfigurationError


@pytest.fixture
def valid_config_file(tmp_path):
    """Create a valid YAML config file."""
    config_content = """
api_key: "test_api_key_12345"
group_id: "test_group_67890"
callback_url: "https://example.com/webhook"
bot_name: "TestBot"
bot_id: "existing_bot_id"
avatar_url: "https://example.com/avatar.jpg"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def minimal_config_file(tmp_path):
    """Create a minimal YAML config file with only required fields."""
    config_content = """
api_key: "test_api_key_12345"
group_id: "test_group_67890"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def missing_api_key_config(tmp_path):
    """Create a config file missing api_key."""
    config_content = """
group_id: "test_group_67890"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def missing_group_id_config(tmp_path):
    """Create a config file missing group_id."""
    config_content = """
api_key: "test_api_key_12345"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def invalid_yaml_file(tmp_path):
    """Create an invalid YAML file."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content: [[[")
    return str(config_file)


@pytest.fixture
def empty_config_file(tmp_path):
    """Create an empty config file."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("")
    return str(config_file)


class TestLoadYamlConfig:
    """Test load_yaml_config function."""

    def test_load_valid_yaml(self, valid_config_file):
        """Test loading a valid YAML config."""
        config = load_yaml_config(valid_config_file)

        assert config["api_key"] == "test_api_key_12345"
        assert config["group_id"] == "test_group_67890"
        assert config["callback_url"] == "https://example.com/webhook"
        assert config["bot_name"] == "TestBot"
        assert config["bot_id"] == "existing_bot_id"
        assert config["avatar_url"] == "https://example.com/avatar.jpg"

    def test_load_minimal_config(self, minimal_config_file):
        """Test loading a minimal config with only required fields."""
        config = load_yaml_config(minimal_config_file)

        assert config["api_key"] == "test_api_key_12345"
        assert config["group_id"] == "test_group_67890"
        assert "callback_url" not in config

    def test_missing_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(ConfigError) as exc_info:
            load_yaml_config("/nonexistent/path/to/config.yaml")

        assert "Config file not found" in str(exc_info.value)

    def test_missing_api_key(self, missing_api_key_config):
        """Test error when api_key is missing."""
        with pytest.raises(ConfigError) as exc_info:
            load_yaml_config(missing_api_key_config)

        assert "api_key is required" in str(exc_info.value)

    def test_missing_group_id(self, missing_group_id_config):
        """Test error when group_id is missing."""
        with pytest.raises(ConfigError) as exc_info:
            load_yaml_config(missing_group_id_config)

        assert "group_id is required" in str(exc_info.value)

    def test_invalid_yaml(self, invalid_yaml_file):
        """Test error on malformed YAML."""
        with pytest.raises(ConfigError) as exc_info:
            load_yaml_config(invalid_yaml_file)

        assert "Invalid YAML" in str(exc_info.value)

    def test_empty_config(self, empty_config_file):
        """Test error on empty config file."""
        with pytest.raises(ConfigError) as exc_info:
            load_yaml_config(empty_config_file)

        assert "Config file is empty" in str(exc_info.value)


class TestGetConfigValue:
    """Test get_config_value function."""

    def test_value_from_config(self):
        """Test getting value from config dict."""
        config = {"api_key": "from_config", "group_id": "group_123"}

        value = get_config_value(config, "api_key")

        assert value == "from_config"

    def test_value_from_env_var(self):
        """Test falling back to environment variable."""
        config = {"api_key": "from_config"}

        with patch.dict(os.environ, {"GROUPME_BOT_NAME": "EnvBot"}):
            value = get_config_value(config, "bot_name")

        assert value == "EnvBot"

    def test_value_from_default(self):
        """Test falling back to default value."""
        config = {"api_key": "from_config"}

        value = get_config_value(config, "timeout", default=30)

        assert value == 30

    def test_config_priority_over_env(self):
        """Test that config value takes priority over environment variable."""
        config = {"bot_name": "ConfigBot"}

        with patch.dict(os.environ, {"GROUPME_BOT_NAME": "EnvBot"}):
            value = get_config_value(config, "bot_name")

        assert value == "ConfigBot"

    def test_env_priority_over_default(self):
        """Test that environment variable takes priority over default."""
        config = {}

        with patch.dict(os.environ, {"GROUPME_TIMEOUT": "60"}):
            value = get_config_value(config, "timeout", default=30)

        assert value == "60"

    def test_none_when_not_found(self):
        """Test that None is returned when no value found and no default."""
        config = {}

        value = get_config_value(config, "nonexistent")

        assert value is None


class TestFromYaml:
    """Test GroupMeBotManager.from_yaml() class method."""

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_from_yaml_with_all_fields(self, mock_create_bot, valid_config_file):
        """Test creating manager from YAML with all fields."""
        mock_create_bot.return_value = {"response": {"bot": {"bot_id": "created_bot_123"}}}

        # The config has bot_id, so it won't auto-create
        manager = GroupMeBotManager.from_yaml(valid_config_file)

        assert manager.api_key == "test_api_key_12345"
        assert manager.group_id == "test_group_67890"
        assert manager.callback_url == "https://example.com/webhook"
        assert manager.primary_bot is not None
        assert manager.primary_bot.name == "TestBot"

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_from_yaml_minimal(self, mock_create_bot, minimal_config_file):
        """Test creating manager from minimal YAML config."""
        mock_create_bot.return_value = {"response": {"bot": {"bot_id": "auto_created_123"}}}

        manager = GroupMeBotManager.from_yaml(minimal_config_file)

        assert manager.api_key == "test_api_key_12345"
        assert manager.group_id == "test_group_67890"
        assert manager.primary_bot is not None
        # Should use default bot_name
        assert manager.primary_bot.name == "System"

    def test_from_yaml_missing_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(ConfigError) as exc_info:
            GroupMeBotManager.from_yaml("/nonexistent/config.yaml")

        assert "Config file not found" in str(exc_info.value)

    def test_from_yaml_invalid_config(self, missing_api_key_config):
        """Test error when config is invalid."""
        with pytest.raises(ConfigError) as exc_info:
            GroupMeBotManager.from_yaml(missing_api_key_config)

        assert "api_key is required" in str(exc_info.value)

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_from_yaml_with_env_fallback(self, mock_create_bot, tmp_path):
        """Test YAML config with environment variable fallback."""
        # Create config without bot_name
        config_content = """
api_key: "test_api_key"
group_id: "test_group"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        mock_create_bot.return_value = {"response": {"bot": {"bot_id": "created_123"}}}

        with patch.dict(os.environ, {"GROUPME_BOT_NAME": "EnvBot"}):
            manager = GroupMeBotManager.from_yaml(str(config_file))

        # Should use bot_name from environment variable
        assert manager.primary_bot.name == "EnvBot"

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_from_yaml_with_all_optional_fields(self, mock_create_bot, tmp_path):
        """Test YAML config with all optional fields."""
        config_content = """
api_key: "test_api_key"
group_id: "test_group"
bot_id: "bot_123"
callback_url: "https://example.com/webhook"
avatar_url: "https://example.com/avatar.jpg"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        manager = GroupMeBotManager.from_yaml(str(config_file))

        assert manager.api_key == "test_api_key"
        assert manager.group_id == "test_group"
        assert manager.callback_url == "https://example.com/webhook"


class TestAutoConfigLoading:
    """Test automatic config file loading."""

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_auto_load_default_config(self, mock_create_bot, tmp_path, monkeypatch):
        """Test auto-loading from groupme_config.yaml when no args provided."""
        # Create default config file in current directory
        config_content = """
api_key: "auto_loaded_key"
group_id: "auto_loaded_group"
bot_id: "auto_loaded_bot"
"""
        config_file = tmp_path / "groupme_config.yaml"
        config_file.write_text(config_content)

        # Change to temp directory so it finds the config
        monkeypatch.chdir(tmp_path)

        # Create manager with no arguments - should auto-load
        manager = GroupMeBotManager()

        assert manager.api_key == "auto_loaded_key"
        assert manager.group_id == "auto_loaded_group"

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_auto_load_from_env_var_path(self, mock_create_bot, tmp_path, monkeypatch):
        """Test auto-loading from path specified in GROUPME_CONFIG_FILE env var."""
        config_content = """
api_key: "env_path_key"
group_id: "env_path_group"
bot_id: "env_path_bot"
"""
        config_file = tmp_path / "custom_config.yaml"
        config_file.write_text(config_content)

        # Set environment variable to point to custom config
        monkeypatch.setenv("GROUPME_CONFIG_FILE", str(config_file))
        monkeypatch.chdir(tmp_path)

        # Create manager with no arguments
        manager = GroupMeBotManager()

        assert manager.api_key == "env_path_key"
        assert manager.group_id == "env_path_group"

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_explicit_config_file_parameter(self, mock_create_bot, tmp_path):
        """Test loading from config_file parameter."""
        config_content = """
api_key: "explicit_key"
group_id: "explicit_group"
bot_id: "explicit_bot"
"""
        config_file = tmp_path / "my_config.yaml"
        config_file.write_text(config_content)

        # Use config_file parameter
        manager = GroupMeBotManager(config_file=str(config_file))

        assert manager.api_key == "explicit_key"
        assert manager.group_id == "explicit_group"

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_params_override_config_file(self, mock_create_bot, tmp_path):
        """Test that explicit parameters override config file values."""
        config_content = """
api_key: "config_key"
group_id: "config_group"
bot_id: "config_bot"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        # Pass both config_file and explicit parameters
        manager = GroupMeBotManager(
            config_file=str(config_file),
            api_key="override_key"
        )

        # Explicit parameter should win
        assert manager.api_key == "override_key"
        # Config value should be used for group_id
        assert manager.group_id == "config_group"

    @patch("group_py.client.GroupMeClient.create_bot")
    def test_no_auto_load_when_params_provided(self, mock_create_bot, tmp_path, monkeypatch):
        """Test that default config is NOT loaded when explicit params provided."""
        # Create default config
        config_content = """
api_key: "should_not_load"
group_id: "should_not_load"
bot_id: "should_not_load"
"""
        config_file = tmp_path / "groupme_config.yaml"
        config_file.write_text(config_content)
        monkeypatch.chdir(tmp_path)

        # Provide explicit parameters - should NOT auto-load config
        manager = GroupMeBotManager(
            api_key="explicit_key",
            group_id="explicit_group",
            bot_id="explicit_bot"
        )

        # Should use explicit values, not config file
        assert manager.api_key == "explicit_key"
        assert manager.group_id == "explicit_group"

    def test_no_auto_load_when_no_config_exists(self, tmp_path, monkeypatch):
        """Test that initialization works normally when no config file exists."""
        monkeypatch.chdir(tmp_path)

        # Should raise ConfigurationError since no config and no params
        with pytest.raises(ConfigurationError):
            GroupMeBotManager()
