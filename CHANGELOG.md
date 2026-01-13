# Changelog

All notable changes to group-py will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-01-12

### Major Features

- **Real-time WebSocket Support** - Connect via WebSocket without webhooks! No server needed.
  ```python
  manager = GroupMeBotManager(
      ...,
      user_id="your_user_id",
      enable_realtime=True,
  )
  ```

- **YAML Configuration** - Load bot config from YAML files for cleaner setup.
  ```python
  manager = GroupMeBotManager.from_yaml("bots.yaml")
  # Or auto-load from groupme_config.yaml
  manager = GroupMeBotManager()
  ```

- **@Mentions Support** - Built-in mention handling with automatic loci calculation.
  ```python
  message.post(
      "Hey @John!",
      mentions=[{"user_id": "123", "name": "John"}]
  )
  ```

- **Global Message Handler** - `@on_any_message` runs for ALL messages before routing.
  ```python
  @manager.on_any_message
  def store_all(message):
      MyDatabase.save(message)
  ```

- **History Fetching** - Pull message history from GroupMe API.
  ```python
  messages = manager.fetch_history(limit=100)
  manager.backfill_history(days=7, callback=store)
  ```

- **Optional Django Models** - Pre-built Django ORM models for message storage.
  ```python
  from group_py.contrib.django.models import GroupMeMessage
  GroupMeMessage.from_message(message).save()
  ```

- **Bot Recovery** - Automatically reuses existing bots on restart to prevent orphans.

### Breaking Changes

- **Removed built-in storage** - Use `@on_any_message` for storage instead.
  See [Migration Guide](docs/MIGRATION_V2_TO_V3.md) for details.

- **Deprecated `message.reply()`** - Use `message.post()` instead.
  Shows DeprecationWarning, will be removed in v4.0.

### New API

- Added `message.post()` - Preferred method for sending messages
- Added `@manager.on_any_message` decorator
- Added `manager.fetch_history()` and `manager.backfill_history()`
- Added `GroupMeBotManager.from_yaml()` class method
- Added `enable_realtime` and `user_id` parameters
- Added `mentions` parameter to `send_message()`
- Added `client.list_bots()` and `client.find_bot()`

### Dependencies

- Added `websocket-client>=1.8.0` (for real-time support)
- Added `pyyaml>=6.0.0` (for YAML config)
- Removed `sqlalchemy` (was for built-in storage)
- Optional: `django>=4.0.0` (install with `group-py[django]`)

### Documentation

- Added comprehensive migration guide
- Added new examples for realtime, YAML config, mentions, and Django storage
- Updated all docstrings

[Full migration guide](docs/MIGRATION_V2_TO_V3.md)

---

## [2.0.0] - 2024-XX-XX

Initial v2.0 release with command routing and webhook handling.

### Features
- Command routing with `@manager.command()` decorator
- Webhook processing
- Bot management
- Built-in SQLAlchemy storage (removed in v3.0)

---

[3.0.0]: https://github.com/mfaircloth/group-py/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/mfaircloth/group-py/releases/tag/v2.0.0
