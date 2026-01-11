# Configuration Guide

group-py v3.0.0 supports multiple ways to configure your bot manager for maximum flexibility.

## Quick Start - Auto-Loading Configuration

The easiest way to get started is to create a `groupme_config.yaml` file:

```bash
# Copy the example file
cp groupme_config.yaml.example groupme_config.yaml

# Edit with your credentials
nano groupme_config.yaml
```

Then simply create your bot manager with no arguments:

```python
from group_py import GroupMeBotManager

# Automatically loads from groupme_config.yaml if it exists
manager = GroupMeBotManager()
```

## Configuration Priority

group-py follows this priority order (highest to lowest):

1. **Explicit parameters** - Direct arguments to `GroupMeBotManager()`
2. **Config file values** - From YAML file
3. **Environment variables** - System environment
4. **Defaults** - Built-in defaults

### Example of Priority

```python
# groupme_config.yaml contains:
# api_key: "from_yaml"
# group_id: "yaml_group"

# This will use "override_key" for api_key, but "yaml_group" for group_id
manager = GroupMeBotManager(api_key="override_key")
```

## Configuration Methods

### Method 1: Auto-Loading (Recommended)

Create `groupme_config.yaml` in your project root:

```yaml
api_key: "your_api_key_here"
group_id: "your_group_id_here"
bot_name: "MyBot"
```

Then use with no arguments:

```python
manager = GroupMeBotManager()  # Auto-loads config!
```

### Method 2: Custom Config File Path

```python
# Via parameter
manager = GroupMeBotManager(config_file="path/to/my_config.yaml")

# Via environment variable
export GROUPME_CONFIG_FILE="path/to/my_config.yaml"
manager = GroupMeBotManager()  # Uses env var path
```

### Method 3: Direct Parameters (Traditional)

```python
manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
    bot_name="MyBot"
)
```

### Method 4: Environment Variables

```bash
export GROUPME_API_KEY="your_api_key"
export GROUPME_GROUP_ID="your_group_id"
export GROUPME_BOT_NAME="MyBot"
```

```python
manager = GroupMeBotManager()  # Uses env vars
```

### Method 5: from_yaml() Class Method

```python
manager = GroupMeBotManager.from_yaml("path/to/config.yaml")
```

## YAML Configuration Reference

### Required Fields

```yaml
# Your GroupMe API key (get from https://dev.groupme.com)
api_key: "abc123..."

# The Group ID where your bot operates
group_id: "456789..."
```

### Optional Fields

```yaml
# Webhook callback URL (only needed for webhook mode)
callback_url: "https://your-server.com/webhook"

# Bot name (default: "System")
bot_name: "MyBot"

# Existing bot ID (if you already created a bot)
bot_id: "existing_bot_id"

# Avatar URL for your bot
avatar_url: "https://i.groupme.com/avatar.jpg"
```

### Complete Example

```yaml
# groupme_config.yaml
api_key: "your_groupme_api_key_here"
group_id: "your_group_id_here"
callback_url: "https://myapp.com/webhook"
bot_name: "Assistant"
bot_id: "bot_123456"
avatar_url: "https://i.groupme.com/bot-avatar.jpg"
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `GROUPME_API_KEY` | Your GroupMe API key | `abc123...` |
| `GROUPME_GROUP_ID` | Group ID | `456789...` |
| `GROUPME_CALLBACK_URL` | Webhook URL | `https://example.com/webhook` |
| `GROUPME_BOT_ID` | Existing bot ID | `bot_123` |
| `GROUPME_BOT_NAME` | Bot name | `MyBot` |
| `GROUPME_CONFIG_FILE` | Custom config file path | `config/bots.yaml` |

## Best Practices

### For Development

Use `groupme_config.yaml` for quick local development:

```yaml
# groupme_config.yaml (in .gitignore)
api_key: "dev_api_key"
group_id: "test_group_id"
bot_name: "DevBot"
```

```python
# main.py
manager = GroupMeBotManager()  # Auto-loads!
```

### For Production

Use environment variables for security:

```bash
# .env file (in .gitignore)
GROUPME_API_KEY=production_key
GROUPME_GROUP_ID=prod_group
GROUPME_CALLBACK_URL=https://api.myapp.com/webhook
```

```python
# main.py
from dotenv import load_dotenv
load_dotenv()

manager = GroupMeBotManager()  # Uses env vars
```

### For Multiple Environments

Use different config files:

```bash
project/
├── config/
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
└── main.py
```

```python
# main.py
import os

env = os.getenv("ENV", "development")
config_file = f"config/{env}.yaml"

manager = GroupMeBotManager(config_file=config_file)
```

## Security Tips

1. **Never commit credentials** - Add `groupme_config.yaml` to `.gitignore`
2. **Use environment variables in production** - More secure than files
3. **Use `.example` files** - Commit `groupme_config.yaml.example` with dummy values
4. **Rotate keys regularly** - Change API keys periodically
5. **Use different keys per environment** - Don't reuse dev keys in production

## Migration from v2.0

If you're upgrading from v2.0, the main change is removing built-in storage:

### v2.0 (Old)
```python
manager = GroupMeBotManager(
    api_key="...",
    group_id="...",
    enable_storage=True  # ❌ Removed in v3.0
)
```

### v3.0 (New)
```python
# Use YAML config
manager = GroupMeBotManager()

# Implement your own storage with @on_any_message
@manager.on_any_message
def store(message):
    # Your custom storage logic
    MyDatabase.save(message)
```

See [MIGRATION_V2_TO_V3.md](./MIGRATION_V2_TO_V3.md) for complete migration guide.

## Troubleshooting

### "ConfigurationError: API key required"

**Solution**: Ensure you have either:
- A `groupme_config.yaml` file with `api_key` set, OR
- `GROUPME_API_KEY` environment variable set, OR
- Pass `api_key` parameter directly

### "Config file not found"

**Solution**:
- Check the file path is correct
- Ensure file is named exactly `groupme_config.yaml` (case-sensitive)
- Or specify path: `GroupMeBotManager(config_file="path/to/file.yaml")`

### Config not loading automatically

**Solution**: Auto-loading only works when **no parameters** are provided. If you pass any parameter, it uses traditional initialization.

```python
# ✓ Auto-loads
manager = GroupMeBotManager()

# ✗ Does NOT auto-load (bot_name provided)
manager = GroupMeBotManager(bot_name="MyBot")

# ✓ Force config file loading even with params
manager = GroupMeBotManager(config_file="config.yaml", bot_name="Override")
```
