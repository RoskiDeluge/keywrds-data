<!-- REFFY:START -->
# Reffy Instructions

These instructions are for AI assistants working in this project.

Always open `@/.reffy/AGENTS.md` when the request:
- Mentions early-stage ideation, exploration, brainstorming, or raw notes
- Needs context before drafting specs or proposals
- Refers to "reffy", "references", "explore", or "context layer"

Use `@/.reffy/AGENTS.md` to learn:
- Reffy workflow for ideation, artifact indexing, and planning scaffolds
- How Reffy owns the runtime while preserving ReffySpec planning files
- How to store and consume ideation context in `.reffy/`

Before performing a Reffy workflow, check `.reffy/skills/` (or run `reffy skill list`) and follow the matching skill.

Keep this managed block so `reffy init` can refresh the instructions.

<!-- REFFY:END -->

<!-- REFFYSPEC:START -->
# ReffySpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/.reffy/reffyspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Needs the authoritative planning/spec workflow for this repo

Use `@/.reffy/reffyspec/AGENTS.md` to learn:
- How to create and apply ReffySpec change proposals
- ReffySpec format and conventions
- Project structure and planning guidelines

Keep this managed block so `reffy init` can refresh the instructions.

<!-- REFFYSPEC:END -->
