# Phase 3: Django Helper Models

**Duration:** 2-3 days

**Status:** 🔴 Not Started

**Branch:** `v3-realtime`

## Overview

Phase 3 adds optional Django models that users can install if they want. These are HELPER models - not required to use group-py.

### What We're Building

1. **GroupMeMessage model** - Django ORM model for messages
2. **GroupMeAttachment model** - Optional attachment storage
3. **Migrations** - Auto-generated Django migrations
4. **Conversion utilities** - `from_message()` and `to_message()`
5. **Optional dependency** - `pip install group-py[django]`

### Key Design Decisions

- **Optional, not required** - Users can ignore this entirely
- **No tight coupling** - Django is an optional extra
- **Standard Django patterns** - Follows Django best practices
- **Example, not prescription** - Users can build their own models

---

## Prerequisites

- [x] **Phase 1 complete** (for `@on_any_message` hook)
- [ ] Django 4.0+ installed (for development/testing)
- [ ] Understanding of Django models and migrations

**Verify prerequisites:**
```bash
# Install Django for development
pip install django>=4.0.0
```

---

## Task Breakdown

### Task 3.1: Create Django App Structure (1.5 days)

**Files to create:**
- `group_py/contrib/__init__.py`
- `group_py/contrib/django/__init__.py`
- `group_py/contrib/django/apps.py`
- `group_py/contrib/django/models.py`
- `group_py/contrib/django/migrations/__init__.py`
- `group_py/contrib/django/migrations/0001_initial.py`

**Implementation Steps:**

#### Step 3.1.1: Create directory structure

```bash
mkdir -p group_py/contrib/django/migrations
touch group_py/contrib/__init__.py
touch group_py/contrib/django/__init__.py
touch group_py/contrib/django/migrations/__init__.py
```

#### Step 3.1.2: Create `contrib/__init__.py`

**Create:** `group_py/contrib/__init__.py`

```python
"""Optional contrib packages for group-py."""
```

#### Step 3.1.3: Create `contrib/django/__init__.py`

**Create:** `group_py/contrib/django/__init__.py`

```python
"""
Optional Django integration for group-py.

Installation:
    1. Install: pip install group-py[django]
    2. Add to INSTALLED_APPS: 'group_py.contrib.django'
    3. Run migrations: python manage.py migrate
    4. Use @on_any_message to store messages

Example:
    from group_py import GroupMeBotManager
    from group_py.contrib.django.models import GroupMeMessage

    manager = GroupMeBotManager(...)

    @manager.on_any_message
    def store_message(message):
        GroupMeMessage.from_message(message).save()
"""

default_app_config = 'group_py.contrib.django.apps.GroupPyConfig'
```

#### Step 3.1.4: Create Django app config

**Create:** `group_py/contrib/django/apps.py`

```python
"""Django app configuration for GroupPy integration."""

from django.apps import AppConfig


class GroupPyConfig(AppConfig):
    """GroupPy Django app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'group_py.contrib.django'
    verbose_name = 'GroupMe Integration'
```

#### Step 3.1.5: Create Django models

**Create:** `group_py/contrib/django/models.py`

See [complete models.py implementation in plan](../../.claude/plans/curried-rolling-parrot.md#phase-3-django-helper-models)

**Key models:**
```python
class GroupMeMessage(models.Model):
    """Django model for GroupMe messages."""
    message_id = models.CharField(max_length=255, primary_key=True)
    group_id = models.CharField(max_length=255, db_index=True)
    user_id = models.CharField(max_length=255, db_index=True)
    user_name = models.CharField(max_length=255)
    text = models.TextField(null=True, blank=True)
    created_at = models.IntegerField(db_index=True)
    sender_type = models.CharField(max_length=20)
    system = models.BooleanField(default=False)
    avatar_url = models.URLField(null=True, blank=True)
    raw_json = models.JSONField()

    @classmethod
    def from_message(cls, message):
        """Create Django model from group-py Message."""
        # Implementation

    def to_message(self):
        """Convert back to group-py Message."""
        # Implementation


class GroupMeAttachment(models.Model):
    """Optional model for storing attachments separately."""
    message = models.ForeignKey(GroupMeMessage, on_delete=models.CASCADE)
    attachment_type = models.CharField(max_length=50)
    data = models.JSONField()
```

#### Step 3.1.6: Generate initial migration

**Create migration:**
```bash
# In a test Django project
python manage.py makemigrations group_py.contrib.django
```

**Or manually create:** `group_py/contrib/django/migrations/0001_initial.py`

See [complete migration in plan](../../.claude/plans/curried-rolling-parrot.md#phase-3-django-helper-models)

**Acceptance Criteria:**
- ✅ Directory structure created
- ✅ App config works
- ✅ Models defined with all fields
- ✅ `from_message()` and `to_message()` implemented
- ✅ Initial migration created

---

### Task 3.2: Add Optional Dependency (0.5 days)

**Files to modify:**
- `pyproject.toml`

**Implementation Steps:**

#### Step 3.2.1: Add Django as optional dependency

**Modify:** `pyproject.toml`

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "flask>=3.0.0",
]
django = [  # NEW
    "django>=4.0.0",
]
```

**Test installation:**
```bash
# Without Django
pip install -e .

# With Django
pip install -e ".[django]"
```

**Acceptance Criteria:**
- ✅ `pip install group-py` works (no Django)
- ✅ `pip install group-py[django]` installs Django
- ✅ Models importable only when Django installed

---

### Task 3.3: Write Tests (1 day)

**Files to create:**
- `tests/unit/test_django.py`

**Implementation Steps:**

#### Step 3.3.1: Create Django test configuration

**Create:** `tests/django_test_settings.py`

```python
"""Minimal Django settings for testing."""

SECRET_KEY = 'test-secret-key'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'group_py.contrib.django',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

#### Step 3.3.2: Write model tests

**Create:** `tests/unit/test_django.py`

```python
"""Unit tests for Django helper models."""

import pytest
import django
from django.conf import settings

# Configure Django
if not settings.configured:
    settings.configure(
        SECRET_KEY='test',
        INSTALLED_APPS=['group_py.contrib.django'],
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
    )
    django.setup()

from group_py.models import Message
from group_py.contrib.django.models import GroupMeMessage, GroupMeAttachment


@pytest.mark.django
class TestDjangoModels:
    """Test Django helper models."""

    def test_from_message(self, mock_message_data):
        """Test creating Django model from Message."""
        message = Message.from_dict(mock_message_data)
        db_msg = GroupMeMessage.from_message(message)

        assert db_msg.message_id == message.id
        assert db_msg.text == message.text
        assert db_msg.user_id == message.user_id
        # ... more assertions

    def test_to_message(self, mock_message_data):
        """Test converting Django model back to Message."""
        original = Message.from_dict(mock_message_data)
        db_msg = GroupMeMessage.from_message(original)
        converted = db_msg.to_message()

        assert converted.id == original.id
        assert converted.text == original.text

    def test_attachment_model(self, mock_message_with_image):
        """Test GroupMeAttachment model."""
        from django.db import connection
        from django.core.management import call_command

        # Create tables
        call_command('migrate', '--run-syncdb', verbosity=0)

        message = Message.from_dict(mock_message_with_image)
        db_msg = GroupMeMessage.from_message(message)
        db_msg.save()

        # Create attachment
        for att in message.attachments:
            GroupMeAttachment.objects.create(
                message=db_msg,
                attachment_type=att.get("type", "unknown"),
                data=att
            )

        # Verify
        attachments = GroupMeAttachment.objects.filter(message=db_msg)
        assert attachments.count() == 1
        assert attachments.first().attachment_type == "image"
```

**Run tests:**
```bash
pytest tests/unit/test_django.py -v -m django
```

**Acceptance Criteria:**
- ✅ `from_message()` works correctly
- ✅ `to_message()` preserves data
- ✅ Models can be saved to database
- ✅ Foreign key relationship works
- ✅ All tests pass

---

### Task 3.4: Create Example (0.5 days)

**Files to create:**
- `examples/django_storage.py`

**Implementation Steps:**

#### Step 3.4.1: Create Django integration example

**Create:** `examples/django_storage.py`

```python
"""
Example: Store messages using Django ORM.

Shows how to use the optional Django helper models.

Setup:
    1. pip install group-py[django]
    2. Add 'group_py.contrib.django' to INSTALLED_APPS
    3. python manage.py migrate
"""

from group_py import GroupMeBotManager
from group_py.contrib.django.models import GroupMeMessage, GroupMeAttachment

# Initialize bot manager
manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
)

# Store ALL messages to Django database
@manager.on_any_message
def store_to_django(message):
    """Store every message using Django ORM."""
    # Skip bot messages if desired
    if message.sender_type == "bot":
        return

    # Create and save message
    db_msg = GroupMeMessage.from_message(message)
    db_msg.save()

    # Optionally store attachments separately
    if message.attachments:
        for att in message.attachments:
            GroupMeAttachment.objects.create(
                message=db_msg,
                attachment_type=att.get("type", "unknown"),
                data=att
            )

# Query stored messages in commands
@manager.command("/search")
def search(message, args):
    """Search message history."""
    results = GroupMeMessage.objects.filter(
        text__icontains=args,
        group_id=message.group_id
    ).order_by('-created_at')[:10]

    if results:
        summary = f"Found {results.count()} messages:\n"
        for msg in results[:3]:
            preview = msg.text[:50] + "..." if len(msg.text) > 50 else msg.text
            summary += f"• {msg.user_name}: {preview}\n"
        message.post(summary)
    else:
        message.post(f"No messages found matching '{args}'")

@manager.command("/stats")
def stats(message, args):
    """Show message statistics."""
    from django.db.models import Count

    total = GroupMeMessage.objects.filter(
        group_id=message.group_id
    ).count()

    message.post(f"Total messages: {total}")

# Backfill history on startup
def store_message(msg):
    GroupMeMessage.from_message(msg).save()

manager.backfill_history(days=7, callback=store_message)
```

**Acceptance Criteria:**
- ✅ Example shows complete integration
- ✅ Shows both storage and querying
- ✅ Demonstrates backfill usage
- ✅ Code is clear and well-commented

---

## Verification Checklist

Before moving to Phase 4, verify:

### Code Quality
- [ ] Models follow Django conventions
- [ ] Migrations are valid
- [ ] Type hints where appropriate
- [ ] Docstrings complete

### Testing
- [ ] Model tests pass
- [ ] Migrations run successfully
- [ ] Can save and query messages
- [ ] Foreign key relationships work

### Features
- [ ] `GroupMeMessage` model complete
- [ ] `GroupMeAttachment` model complete
- [ ] `from_message()` works
- [ ] `to_message()` works
- [ ] Migrations generated
- [ ] Optional dependency setup correctly

### Documentation
- [ ] Docstrings explain usage
- [ ] Example is complete and clear
- [ ] Installation instructions accurate

### Git
- [ ] All changes committed
- [ ] Meaningful commit messages

**Final verification:**
```bash
# Test installation
pip install -e ".[django]"

# Test migrations
python -c "
import django
from django.conf import settings
settings.configure(
    INSTALLED_APPS=['group_py.contrib.django'],
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
)
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=2)
print('✓ Migrations work')
"
```

---

## Troubleshooting

### "No module named 'django'"

**Solution:** Install with Django extra:
```bash
pip install group-py[django]
```

### Migrations not found

**Solution:** Ensure `group_py.contrib.django` in INSTALLED_APPS

### JSONField not working

**Solution:** Requires PostgreSQL or Django 3.1+ with SQLite

---

## Next Steps

Once Phase 3 is complete:

1. **Commit Phase 3:**
   ```bash
   git add .
   git commit -m "Phase 3: Django integration complete

   - Add optional Django helper models
   - Add GroupMeMessage and GroupMeAttachment models
   - Add from_message() and to_message() utilities
   - Add migrations
   - Add Django as optional dependency
   - Add comprehensive example"
   ```

2. **Proceed to Phase 4:** [PHASE_4_FINALIZATION.md](./PHASE_4_FINALIZATION.md)

---

## Estimated Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| 3.1 Django App | 1.5 days | Phase 1 |
| 3.2 Optional Dependency | 0.5 days | Task 3.1 |
| 3.3 Tests | 1 day | Task 3.1 |
| 3.4 Example | 0.5 days | Task 3.1 |

**Total: 3-4 days**

**Note:** Phase 3 can run in parallel with Phase 2 since they don't depend on each other (both depend on Phase 1).
