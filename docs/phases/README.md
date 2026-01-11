# Group-Py v3.0.0 - Implementation Phases

This directory contains detailed implementation plans for each phase of the v3.0.0 upgrade.

## Overview

**Total Timeline:** 2.5-3.5 weeks

**Branch:** `v3-realtime`

**Strategy:** Incremental implementation with testing at each phase

## Phase Index

### [Phase 1: Foundation](./PHASE_1_FOUNDATION.md) (1 week)
**Status:** 🔴 Not Started

**Deliverables:**
- ✅ Mentions support with auto-calculated loci
- ✅ YAML configuration loader
- ✅ Global message handler (`@on_any_message`)
- ✅ History fetching from GroupMe API
- ✅ Remove built-in storage

**Key Files:**
- Modify: `group_py/client.py`, `group_py/sender.py`, `group_py/bot.py`
- Create: `group_py/config.py`
- Delete: `group_py/storage.py`

---

### [Phase 2: Realtime WebSocket](./PHASE_2_REALTIME.md) (1-2 weeks)
**Status:** 🔴 Not Started (Requires Phase 1)

**Deliverables:**
- ✅ Faye/Bayeux WebSocket client
- ✅ Real-time message reception
- ✅ Auto-reconnect on disconnect
- ✅ Integration with bot manager

**Key Files:**
- Create: `group_py/realtime.py`
- Modify: `group_py/bot.py`

---

### [Phase 3: Django Integration](./PHASE_3_DJANGO.md) (2-3 days)
**Status:** 🔴 Not Started (Requires Phase 1)

**Deliverables:**
- ✅ Optional Django helper models
- ✅ Database migrations
- ✅ Conversion utilities

**Key Files:**
- Create: `group_py/contrib/django/` (entire directory)

---

### [Phase 4: Finalization](./PHASE_4_FINALIZATION.md) (3-5 days)
**Status:** 🔴 Not Started (Requires Phases 1-3)

**Deliverables:**
- ✅ `message.post()` method
- ✅ Deprecate `message.reply()`
- ✅ Update all examples
- ✅ Complete documentation
- ✅ Migration guide

**Key Files:**
- Modify: `group_py/models.py`, all examples, `README.md`
- Create: `docs/MIGRATION_V2_TO_V3.md`, `CHANGELOG.md`

---

## How to Use These Docs

### For Review

Each phase document contains:
1. **Overview** - What this phase accomplishes
2. **Prerequisites** - What must be done first
3. **Task Breakdown** - Detailed implementation tasks
4. **Acceptance Criteria** - How to know it's done
5. **Testing Requirements** - Tests that must pass
6. **Verification Checklist** - Final checks before moving on

### For Execution

When ready to implement a phase:

1. **Review the phase document** thoroughly
2. **Verify prerequisites** are met
3. **Execute tasks** in order
4. **Run tests** after each major task
5. **Verify acceptance criteria** before moving to next phase

### Status Indicators

- 🔴 Not Started
- 🟡 In Progress
- 🟢 Complete
- ⚠️ Blocked

## Dependencies Between Phases

```
Phase 1 (Foundation)
    ↓
    ├─→ Phase 2 (Realtime)
    ├─→ Phase 3 (Django)
    └─→ Phase 4 (Finalization)
        ↓
    v3.0.0 Release
```

**Note:** Phases 2 and 3 can be done in parallel after Phase 1 is complete.

## Quick Reference

### Phase 1 Checklist
- [ ] Mentions support implemented
- [ ] YAML config loader works
- [ ] `@on_any_message` decorator works
- [ ] History fetching works with pagination
- [ ] Built-in storage removed
- [ ] All unit tests pass
- [ ] Examples updated

### Phase 2 Checklist
- [ ] Faye client connects to WebSocket
- [ ] Messages received via WebSocket
- [ ] Auto-reconnect works
- [ ] Filters ping/typing events
- [ ] Integration tests pass

### Phase 3 Checklist
- [ ] Django models created
- [ ] Migrations work
- [ ] `from_message()` works
- [ ] Optional dependency setup
- [ ] Example works

### Phase 4 Checklist
- [ ] `post()` method implemented
- [ ] `reply()` shows deprecation warning
- [ ] All examples updated
- [ ] README rewritten
- [ ] Migration guide complete
- [ ] All tests pass

## Getting Started

**Ready to begin?**

```bash
# Ensure you're on the v3-realtime branch
git checkout v3-realtime

# Start with Phase 1
# Read: docs/phases/PHASE_1_FOUNDATION.md
```

## Notes

- Each phase is designed to be independently testable
- Breaking changes are isolated to Phase 1 (storage removal) and Phase 4 (reply deprecation)
- All phases include comprehensive testing requirements
- Documentation is written incrementally with each phase
