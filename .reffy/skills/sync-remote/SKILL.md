---
name: sync-remote
description: Publish and inspect the local .reffy/ workspace on a Paseo-backed remote.
triggers: ["remote sync", "push workspace", "paseo", "remote status"]
commands: ["reffy remote init", "reffy remote status", "reffy remote push", "reffy remote snapshot"]
managed: true
---

## When to use this skill
Use this to link, publish, or inspect the shared remote workspace projection.

## Required environment
- `PASEO_ENDPOINT` — the Paseo endpoint URL (never persisted).
- `PASEO_TOKEN` — the bearer token (never persisted by the CLI).

Provide them either by exporting them in your shell or by placing them in a
`.env` file at the repo root — every `reffy remote` command auto-loads `.env`
(use `--env-file PATH` to point at a different file). Exported shell vars take
precedence over `.env`.

## Steps
1. Ensure both values are available via the shell or `.env`; the CLI fails fast and names a missing one.
2. First time: `reffy remote init --provision` to create the workspace and mint a token. Save the token immediately.
3. `reffy remote status` to confirm linkage and identity.
4. `reffy remote push` to import the full local `.reffy/` tree.
5. `reffy remote snapshot` / `ls` / `cat` to inspect the remote projection.

## Failure modes
- A missing token makes the stored identifiers in `.reffy/state/remote.json` inert — set `PASEO_TOKEN`.
