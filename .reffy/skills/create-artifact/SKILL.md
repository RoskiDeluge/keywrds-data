---
name: create-artifact
description: Capture ideation context as a Reffy artifact and register it in the manifest.
triggers: ["new artifact", "capture idea", "add note", "reindex"]
commands: ["reffy reindex", "reffy validate"]
managed: true
---

## When to use this skill
Use this when you have raw ideation, exploration, or research context to capture before any formal planning.

## Steps
1. Write the context as a markdown file under `.reffy/artifacts/` with a clear, stable, kebab-case filename.
2. Run `reffy reindex` to add the new file to `.reffy/manifest.json`.
3. Run `reffy validate` to confirm the manifest still satisfies the v1 contract.
4. Confirm the artifact appears in the manifest with the expected name and id.

## Failure modes
- If `reffy validate` reports an invalid manifest, fix the reported entry before continuing — do not hand-edit ids.
- Keep artifacts exploratory; do not duplicate full proposal or spec content here.
