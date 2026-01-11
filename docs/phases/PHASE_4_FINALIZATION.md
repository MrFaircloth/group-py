# Phase 4: Finalization & Documentation

**Duration:** 3-5 days

**Status:** 🔴 Not Started

**Branch:** `v3-realtime`

## Overview

Phase 4 completes the v3.0.0 release by implementing the final breaking change (`reply()` → `post()`), updating all examples, and writing comprehensive documentation.

### What We're Building

1. **message.post() method** - New preferred API
2. **Deprecate message.reply()** - Soft breaking change with warning
3. **Update all examples** - Use post() and show new features
4. **New examples** - Realtime, YAML config, mentions, storage
5. **Complete documentation** - README, migration guide, changelog

### Why This Comes Last

- All features complete, can document accurately
- Examples depend on Phases 1-3
- Breaking change is the final step before release

---

## Prerequisites

- [x] **Phase 1 complete** - Foundation features
- [x] **Phase 2 complete** - Realtime WebSocket
- [x] **Phase 3 complete** - Django models
- [ ] All tests passing

**Verify prerequisites:**
```bash
# All previous phases complete
git log --oneline | grep -E "Phase [123]"

# All tests pass
pytest -v
```

---

## Task Breakdown

### Task 4.1: Implement message.post() (1 day)

**Files to modify:**
- `group_py/models.py`
- `group_py/bot.py`

**Implementation Steps:**

#### Step 4.1.1: Add post() method to Message dataclass

**Location:** `group_py/models.py`

**Add `_send_callback` field:**
```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable

@dataclass
class Message:
    """GroupMe message data model."""

    id: str
    text: Optional[str]
    user_id: str
    name: str
    group_id: str
    created_at: int
    system: bool
    sender_type: str
    avatar_url: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None

    # NEW: Callback injected by bot manager
    _send_callback: Optional[Callable] = field(default=None, repr=False)
```

**Add post() method:**
```python
def post(self, text: str, **kwargs):
    """
    Post a message to the group (v3.0+).

    This is the preferred method name in v3.0. It's clearer than "reply"
    since you're not always replying - you're posting to the group.

    Args:
        text: Message text to post
        **kwargs: Additional arguments passed to send_message()
            - image_url: Optional image URL
            - mentions: Optional list of mention dicts
            - attachments: Optional custom attachments

    Returns:
        API response dict

    Raises:
        NotImplementedError: If callback not initialized

    Example:
        @manager.command("/hello")
        def hello(message, args):
            message.post("Hello!")

        @manager.command("/tag")
        def tag(message, args):
            message.post(
                f"Hey @{args}!",
                mentions=[{"user_id": "123", "name": args}]
            )
    """
    if self._send_callback is None:
        raise NotImplementedError(
            "Post method not initialized. This message was not created "
            "by GroupMeBotManager.process_webhook()"
        )
    return self._send_callback(text, **kwargs)
```

**Add deprecated reply() method:**
```python
import warnings

def reply(self, text: str, **kwargs):
    """
    Reply to this message (DEPRECATED - use post() instead).

    .. deprecated:: 3.0.0
        Use :meth:`post` instead. This method will be removed in v4.0.

    The name "reply" is misleading since you're not always replying to
    something - you're just posting a message to the group.

    Args:
        text: Message text
        **kwargs: Additional arguments passed to post()

    Returns:
        API response dict

    Example (deprecated):
        message.reply("Hello!")  # Shows DeprecationWarning

    Example (recommended):
        message.post("Hello!")
    """
    warnings.warn(
        "Message.reply() is deprecated and will be removed in v4.0. "
        "Use message.post() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return self.post(text, **kwargs)
```

#### Step 4.1.2: Update bot.py to inject callback

**Location:** `group_py/bot.py` in `process_webhook()`

**Update injection:**
```python
def process_webhook(self, data: dict) -> None:
    """Process a GroupMe webhook payload."""
    # Parse the message
    message = Message.from_dict(data)

    # NEW: Inject send callback for post() method
    message._send_callback = lambda text, **kwargs: self.send_message(text, **kwargs)

    # Rest of processing...
```

#### Step 4.1.3: Write tests

**Create:** `tests/unit/test_post_method.py`

```python
"""Tests for message.post() method."""

import pytest
import warnings


def test_post_method(mock_requests, mock_message_data):
    """Test that post() sends message."""
    from group_py import GroupMeBotManager

    manager = GroupMeBotManager(api_key="test", group_id="test")

    @manager.command("/test")
    def test_cmd(message, args):
        message.post("Response")

    manager.process_webhook(mock_message_data)
    # Verify send_message was called


def test_reply_shows_deprecation_warning(mock_requests, mock_message_data):
    """Test that reply() shows deprecation warning."""
    from group_py import GroupMeBotManager

    manager = GroupMeBotManager(api_key="test", group_id="test")

    @manager.command("/test")
    def test_cmd(message, args):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            message.reply("Response")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "post()" in str(w[0].message)


def test_post_without_callback_raises_error():
    """Test that post() without callback raises error."""
    from group_py.models import Message

    message = Message.from_dict({"id": "1", "text": "hi", ...})

    with pytest.raises(NotImplementedError):
        message.post("test")
```

**Run tests:**
```bash
pytest tests/unit/test_post_method.py -v
```

**Acceptance Criteria:**
- ✅ `post()` method works
- ✅ `reply()` shows deprecation warning
- ✅ Both methods call same underlying function
- ✅ Error raised if callback not set
- ✅ All tests pass

---

### Task 4.2: Update All Examples (1 day)

**Files to modify:**
- `examples/flask_bot.py`
- `examples/django_bot.py`
- `examples/multi_bot.py`
- `examples/send_only_bot.py`

**Files to create:**
- `examples/realtime_bot.py`
- `examples/yaml_config_bot.py`
- `examples/mentions_bot.py`
- `examples/bots.yaml.example`

**Implementation Steps:**

#### Step 4.2.1: Update existing examples to use post()

**Find and replace** in all examples:
```bash
# Find all reply() usage
grep -r "message.reply(" examples/

# Replace with post()
sed -i '' 's/message\.reply(/message.post(/g' examples/*.py
```

**Manually verify** each replacement makes sense.

#### Step 4.2.2: Create realtime bot example

**Create:** `examples/realtime_bot.py`

```python
"""
Example: Real-time WebSocket bot (no webhook needed).

This bot connects via WebSocket to receive messages in real-time.
No need to expose an HTTP endpoint!
"""

from group_py import GroupMeBotManager

manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
    user_id="your_user_id",      # Required for realtime
    enable_realtime=True,         # Enable WebSocket
)

print("✓ Bot connected via WebSocket - no webhook needed!")

# Log all messages
@manager.on_any_message
def log_all(message):
    print(f"[{message.name}]: {message.text}")

# Commands work the same
@manager.command("/hello")
def hello(message, args):
    message.post(f"Hi {message.name}!")

# Keep program running
if __name__ == "__main__":
    print("Bot is running... Press Ctrl+C to stop")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        manager.realtime_manager.stop()
```

#### Step 4.2.3: Create YAML config example

**Create:** `examples/yaml_config_bot.py` and `examples/bots.yaml.example`

See [complete examples in plan](../../.claude/plans/curried-rolling-parrot.md#phase-4-breaking-changes--finalization)

#### Step 4.2.4: Create mentions example

**Create:** `examples/mentions_bot.py`

See [complete example in plan](../../.claude/plans/curried-rolling-parrot.md#phase-4-breaking-changes--finalization)

#### Step 4.2.5: Create storage examples directory

```bash
mkdir -p examples/storage
```

**Create:**
- `examples/storage/django_storage.py`
- `examples/storage/simple_json.py`
- `examples/storage/sqlalchemy_storage.py`

See [complete examples in plan](../../.claude/plans/curried-rolling-parrot.md#phase-4-breaking-changes--finalization)

**Acceptance Criteria:**
- ✅ All existing examples use `post()`
- ✅ All examples run without errors
- ✅ New examples demonstrate v3.0 features
- ✅ Storage examples show different databases
- ✅ Examples are well-documented

---

### Task 4.3: Complete Documentation (2-3 days)

**Files to create:**
- `docs/MIGRATION_V2_TO_V3.md`
- `CHANGELOG.md`

**Files to update:**
- `README.md` (major rewrite)
- All docstrings

**Implementation Steps:**

#### Step 4.3.1: Write migration guide

**Create:** `docs/MIGRATION_V2_TO_V3.md`

See [complete migration guide in plan](../../.claude/plans/curried-rolling-parrot.md#migration-guide-v20--v30)

**Key sections:**
- Breaking changes overview
- Step-by-step migration
- Storage migration (most important)
- Common migration patterns
- Troubleshooting

#### Step 4.3.2: Write changelog

**Create:** `CHANGELOG.md`

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [3.0.0] - 2026-XX-XX

### 🎉 Major Features

- **Real-time WebSocket Support** - Connect via WebSocket without webhooks
- **YAML Configuration** - Load bot config from YAML files
- **Mentions Support** - Auto-calculate loci for @mentions
- **Global Message Handler** - `@on_any_message` for all messages
- **History Fetching** - Pull message history from GroupMe API
- **Optional Django Models** - Pre-built Django models

### ⚠️ Breaking Changes

- **Removed built-in storage** - Users implement storage with `@on_any_message`
- **Deprecated `message.reply()`** - Use `message.post()` instead
- **Removed SQLAlchemy dependency** - Package is lighter

### ✨ New Features

- Added `GroupMeBotManager.from_yaml()`
- Added `@manager.on_any_message` decorator
- Added `mentions` parameter to `send_message()`
- Added `fetch_history()` and `backfill_history()`
- Added `enable_realtime` and `user_id` parameters
- Added `message.post()` method

### 📦 Dependencies

- Added `websocket-client>=1.8.0`
- Added `pyyaml>=6.0.0`
- Removed `sqlalchemy>=2.0.0`
- Optional: `django>=4.0.0`

[Full migration guide →](docs/MIGRATION_V2_TO_V3.md)

## [2.0.0] - 2025-XX-XX

Initial v2.0 release

[3.0.0]: https://github.com/mfaircloth/group-py/compare/v2.0.0...v3.0.0
```

#### Step 4.3.3: Rewrite README.md

**Update:** `README.md`

See [complete README in plan](../../.claude/plans/curried-rolling-parrot.md#readmemd-major-rewrite)

**Key sections:**
- What's new in v3.0 (prominent)
- Quick start (updated for v3.0)
- Features list (updated)
- Core concepts (all new features)
- API reference (updated)
- Migration guide link
- Examples

#### Step 4.3.4: Update all docstrings

**Review and update:**
- All function/method docstrings
- All class docstrings
- Module-level docstrings
- Add examples where helpful

**Verify:**
```bash
# Check for missing docstrings
python -c "
import group_py
import inspect
for name, obj in inspect.getmembers(group_py):
    if inspect.isfunction(obj) and not obj.__doc__:
        print(f'Missing docstring: {name}')
"
```

**Acceptance Criteria:**
- ✅ Migration guide complete and clear
- ✅ CHANGELOG accurate and comprehensive
- ✅ README rewritten for v3.0
- ✅ All docstrings present and helpful
- ✅ Examples in docstrings work

---

### Task 4.4: Final Testing & Release Prep (1 day)

**Files to update:**
- `pyproject.toml` (version number)
- `group_py/__init__.py` (version number)

**Implementation Steps:**

#### Step 4.4.1: Update version numbers

**Update:** `pyproject.toml`
```toml
[project]
version = "3.0.0"  # Update from 2.0.0
```

**Update:** `group_py/__init__.py`
```python
__version__ = "3.0.0"
```

#### Step 4.4.2: Run full test suite

```bash
# All unit tests
pytest -v

# All integration tests
pytest -m integration -v

# Check coverage
pytest --cov=group_py --cov-report=html --cov-report=term

# Code style
black --check .
```

#### Step 4.4.3: Test installation

```bash
# Test local installation
pip install -e .

# Test with optional Django
pip install -e ".[django]"

# Verify imports
python -c "
from group_py import GroupMeBotManager
from group_py.contrib.django.models import GroupMeMessage
print('✓ All imports work')
"
```

#### Step 4.4.4: Test all examples

```bash
# Syntax check all examples
for file in examples/*.py examples/**/*.py; do
    python -m py_compile "$file"
done
```

#### Step 4.4.5: Create release checklist

**Create:** `docs/RELEASE_CHECKLIST.md`

```markdown
# v3.0.0 Release Checklist

## Code
- [ ] All tests pass
- [ ] Code style clean (black)
- [ ] No TODO/FIXME in code
- [ ] Version numbers updated

## Documentation
- [ ] README accurate
- [ ] CHANGELOG complete
- [ ] Migration guide clear
- [ ] All examples work
- [ ] Docstrings complete

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Examples syntax-check
- [ ] Manual testing done

## Git
- [ ] All changes committed
- [ ] Branch: v3-realtime
- [ ] Ready to merge to main

## PyPI
- [ ] Build distribution
- [ ] Test on test.pypi.org
- [ ] Publish to pypi.org

## Post-Release
- [ ] GitHub release created
- [ ] Tag created: v3.0.0
- [ ] Update beanbot project
- [ ] Announce on social media
```

**Acceptance Criteria:**
- ✅ Version numbers updated
- ✅ All tests pass
- ✅ Installation works
- ✅ Examples run
- ✅ Release checklist complete

---

## Verification Checklist

Before release, verify:

### Code Quality
- [ ] All code formatted with black
- [ ] All imports organized
- [ ] No unused code
- [ ] Type hints complete

### Testing
- [ ] 100% of critical paths tested
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual testing complete

### Documentation
- [ ] README complete and accurate
- [ ] Migration guide clear
- [ ] CHANGELOG accurate
- [ ] All examples work
- [ ] Docstrings complete

### Breaking Changes
- [ ] All breaking changes documented
- [ ] Migration guide addresses all changes
- [ ] Deprecation warnings shown

### Git
- [ ] All changes committed
- [ ] Commit messages clear
- [ ] Branch ready to merge

**Final verification command:**
```bash
# Run everything
pytest -v --cov=group_py
black --check .
python -m py_compile examples/**/*.py

# Verify version
python -c "import group_py; print(group_py.__version__)"  # Should be 3.0.0
```

---

## Release Process

### Step 1: Final Commit

```bash
git add .
git commit -m "Phase 4: v3.0.0 complete

- Add message.post() method
- Deprecate message.reply() with warning
- Update all examples to use post()
- Add realtime, YAML config, mentions examples
- Add storage examples (Django, SQLite, JSON)
- Complete README rewrite
- Add migration guide v2.0 → v3.0
- Add CHANGELOG
- Update all documentation
- Version 3.0.0"
```

### Step 2: Merge to Main

```bash
git checkout main
git merge v3-realtime
git push origin main
```

### Step 3: Create Tag

```bash
git tag -a v3.0.0 -m "Release v3.0.0

Major Features:
- Real-time WebSocket support
- YAML configuration
- Mentions support
- Global message handler
- History fetching
- Optional Django models

Breaking Changes:
- Removed built-in storage
- Deprecated message.reply()
- See docs/MIGRATION_V2_TO_V3.md"

git push origin v3.0.0
```

### Step 4: Build and Publish

```bash
# Build distribution
python -m build

# Test on test.pypi.org
python -m twine upload --repository testpypi dist/*

# Publish to pypi.org
python -m twine upload dist/*
```

### Step 5: GitHub Release

1. Go to GitHub → Releases → Create new release
2. Choose tag: v3.0.0
3. Title: "v3.0.0 - Real-time WebSocket Support"
4. Description: Copy from CHANGELOG.md
5. Attach built distributions
6. Publish release

---

## Troubleshooting

### Deprecation warnings in tests

**Expected!** Tests should show deprecation warnings for `reply()`.

### Examples failing

**Check:**
- All use `post()` not `reply()`
- Syntax is valid
- Dependencies installed

### Documentation incomplete

**Verify:**
- All new features documented
- Migration guide covers all breaking changes
- Examples demonstrate all features

---

## Success Criteria

✅ **v3.0.0 is complete when:**
- All phases 1-4 complete
- All tests passing
- Documentation complete and accurate
- Examples work and demonstrate features
- Breaking changes clearly documented
- Migration guide is clear
- Ready to publish to PyPI

---

## Post-Release Tasks

1. **Monitor Issues** - Watch for bug reports
2. **Update beanbot** - Migrate to v3.0.0
3. **Gather Feedback** - User experience
4. **Plan v3.1.0** - Improvements and new features

---

## Estimated Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| 4.1 post() Method | 1 day | Phases 1-3 |
| 4.2 Update Examples | 1 day | Task 4.1 |
| 4.3 Documentation | 2-3 days | Tasks 4.1-4.2 |
| 4.4 Testing & Prep | 1 day | Task 4.3 |

**Total: 5-6 days**
