## Context
The development workspace uses `dbw_sql_dev_westus2` with `development`, `raw`, `refactored`, and `primary` schemas. The production workspace uses `keywrds_data.production`. Human production users are read-only, and the dedicated publisher service principal is the only non-admin identity allowed to create or modify production tables.

## Goals / Non-Goals
- Goals:
  - Authenticate GitHub Actions without a Databricks token, client secret, or Azure client secret.
  - Restrict production deployment to the repository's GitHub `production` environment.
  - Parameterize development and production catalog/schema targets in a Databricks bundle.
  - Preserve least-privilege Unity Catalog access for the publisher.
- Non-Goals:
  - Publish a model before an approved primary model definition exists.
  - Copy tables directly from the workspace-bound development catalog into production.
  - Give the publisher catalog administration, schema ownership, secret-management, or external-location privileges.

## Decisions
- Decision: Use native Databricks GitHub OIDC federation with `DATABRICKS_AUTH_TYPE=github-oidc`.
  - Rationale: It exchanges the GitHub workload token directly for Databricks OAuth and avoids all long-lived deployment secrets.
- Decision: Bind the federation policy to `repo:RoskiDeluge/keywrds-data:environment:production`.
  - Rationale: The trust is limited to one repository and one protected deployment environment rather than every workflow or branch.
- Decision: Keep production deployment manually triggered initially.
  - Rationale: Model promotion is an explicit approval event until automated tests and release criteria are mature.
- Decision: Deploy model definitions through a multi-target bundle and recompute production outputs from governed production sources.
  - Rationale: This preserves workspace isolation and prevents development data from becoming an implicit production dependency.
- Decision: Grant source reads at schema scope and destination writes at `keywrds_data.production` schema scope.
  - Rationale: The publisher receives only the data-plane permissions required to read sources and materialize approved production tables.

## Reffy Inputs
- `databricks_initial_table_scope.md`
- `databricks_native_ingest_judgment.md`

## Open Questions
- Production model resources will be added to the bundle as primary model definitions are approved.
