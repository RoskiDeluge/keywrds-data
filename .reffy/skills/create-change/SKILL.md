---
name: create-change
description: Turn one or more ideation artifacts into a ReffySpec change proposal.
triggers: ["new change", "plan create", "turn artifact into proposal"]
commands: ["reffy plan create", "reffy plan validate"]
managed: true
---

## When to use this skill
Use this when ideation has converged and you are ready to scaffold a formal ReffySpec change from one or more artifacts.

## Steps
1. Pick the source artifacts in `.reffy/artifacts/` that inform the change.
2. Run `reffy plan create --change-id <kebab-id> --artifacts <files> --title "<title>"`.
3. Fill in the scaffolded `proposal.md`, `design.md`, `tasks.md`, and `specs/<capability>/spec.md` deltas.
   Each delta requirement needs at least one `#### Scenario:`.
4. Run `reffy plan validate <change-id>` and resolve every error before implementing.

## Failure modes
- If validation reports a missing scenario block, add at least one scenario to each requirement.
- Use a unique verb-led, kebab-case `change-id`.
