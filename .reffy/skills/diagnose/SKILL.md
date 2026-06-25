---
name: diagnose
description: Diagnose Reffy workspace health and resolve common failure classes.
triggers: ["diagnose", "doctor", "validate", "workspace health"]
commands: ["reffy doctor", "reffy validate"]
managed: true
---

## When to use this skill
Use this first when a Reffy command misbehaves in an unfamiliar repo.

## Steps
1. Run `reffy doctor` for the required/optional check list.
2. Run `reffy validate` to confirm the manifest contract.
3. Resolve each failure by class:
   - Missing `.reffy/` or `AGENTS.md`: run `reffy init`.
   - Legacy `.references/` workspace: run `reffy init`.
   - Invalid manifest: fix the reported entry, then re-run `reffy validate`.
   - Skill command drift: update the stale skill's `commands` list.

## Failure modes
- A non-zero exit from `reffy doctor` means a required check failed; address required failures before optional warnings.
