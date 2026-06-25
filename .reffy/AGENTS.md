# Reffy Instructions

These instructions are for AI assistants working in this project.

## TL;DR Checklist

- Decide whether Reffy ideation is needed for this request.
- If needed, read existing context in `.reffy/artifacts/`.
- Add/update exploratory artifacts and keep them concise.
- Run `reffy reindex` and `reffy validate` after artifact changes.
- Use `reffy summarize --output json` and `reffy plan create` to turn artifact context into planning scaffolds.
- Before performing a Reffy workflow, check `.reffy/skills/` (or run `reffy skill list`) and follow the matching skill.

## When To Use Reffy

Use Reffy first when the request:
- Mentions early-stage ideation, exploration, brainstorming, or raw notes
- Needs context gathering before drafting a concrete implementation plan
- Refers to "reffy", "references", "explore", "context layer", or research artifacts

## When To Skip Reffy

You can skip Reffy when the request is:
- A narrow bug fix that does not need exploratory context
- A small refactor with no requirement/design ambiguity
- A formatting, typing, or tooling-only update with clear scope

## Reffy Workflow

1. Read existing artifacts in `.reffy/artifacts/`.
2. Add or update artifacts to capture exploratory context.
3. Run `reffy reindex` to index newly added files into `.reffy/manifest.json`.
4. Run `reffy validate` to verify manifest contract compliance.
5. Run `reffy plan create` to generate proposal/tasks/spec scaffolds from selected artifacts when planning is ready.

## Relationship To ReffySpec

- Reffy owns ideation artifacts, manifest metadata, and native planning scaffolds.
- ReffySpec is the planning subsystem inside Reffy.
- The vendored fork at `/.vendor/ReffySpec` is reference-only for v1; first-party behavior lives in this repo.
- Reffy is the primary runtime authority for this project.
- ReffySpec files live under `.reffy/reffyspec/` as the canonical planning layout.
- Do not duplicate full proposal/spec content in Reffy artifacts; generate and link planning outputs from them.

## ReffySpec Citation Rules

When a ReffySpec proposal is informed by Reffy artifacts:
- After ideation approval, run `reffy summarize --output json` to shortlist candidate artifacts.
- Include a short "Reffy References" subsection in `proposal.md` (or design notes if more appropriate).
- Cite only artifact filenames that directly informed the proposal's problem, scope, decisions, or constraints.
- Cite artifact filenames and intent, for example:
  - `testing.md` - early constraints and tradeoffs for manifest validation
- Do not include generic process artifacts or unrelated notes just because they exist.
- Keep citations at proposal/design level; task-by-task traceability is optional unless the change is high risk.
- If no Reffy artifacts informed the change, explicitly state "No Reffy references used."

### Reusable Proposal Snippet

Use this in `.reffy/reffyspec/changes/<change-id>/proposal.md`:

```md
## Reffy References
- `artifact-name.md` - short note about how it informed this proposal
```

If none were used:

```md
## Reffy References
No Reffy references used.
```

## Artifact Conventions

- Treat `.reffy/` as a repository-local guidance and ideation context layer.
- Keep artifact names clear and stable.
- Prefer markdown notes for exploratory content.
- Keep manifests machine-readable and schema-compliant (version 1).
