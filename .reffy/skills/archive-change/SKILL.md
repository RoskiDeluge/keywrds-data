---
name: archive-change
description: Complete and archive a shipped ReffySpec change, merging its delta into canonical specs.
triggers: ["archive change", "ship change", "plan archive", "merge spec"]
commands: ["reffy plan validate", "reffy plan archive", "reffy spec show"]
managed: true
---

## When to use this skill
Use this once a change is implemented and verified and you want to fold its spec delta into canonical truth.

## Steps
1. Confirm every task in `tasks.md` is checked off.
2. Run `reffy plan validate <change-id>` one last time.
3. Run `reffy plan archive <change-id>` to move the change under `changes/archive/<date>-<change-id>/` and merge its delta specs.
4. Verify the merge with `reffy spec show <capability>`.

## Failure modes
- If archive reports unmerged or conflicting requirements, inspect the delta against the canonical spec before retrying.
