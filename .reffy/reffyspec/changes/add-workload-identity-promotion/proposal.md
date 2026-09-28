# Change: Add workload-identity production promotion

## Why
Production publication should be performed by an auditable deployment identity rather than a human administrator. The repository currently has no CI configuration, bundle definition, or secretless authentication path, even though Unity Catalog now separates broad development access from read-only production access.

## What Changes
- Add a two-target Databricks Declarative Automation Bundle for the development and production workspaces.
- Add a manually triggered GitHub Actions production deployment that authenticates directly to Databricks through GitHub OIDC.
- Bind the GitHub `production` environment to the dedicated `keywrds-data-prod-publisher` Databricks service principal.
- Grant the publisher read-only access to the existing governed source schemas and table-publication access only to `keywrds_data.production`.
- Document the development medallion layers and the rule that approved model code is deployed and recomputed in production instead of copying development data.

## Impact
- Affected specs: `workload-identity-promotion`
- Affected code: `databricks.yml`, `.github/workflows/deploy-production.yml`, `README.md`
- Affected external configuration: Databricks federation policy, Unity Catalog grants, GitHub `production` environment variables

## Supersedes
None

## Reffy References
- `databricks_initial_table_scope.md` - identifies the initial Postgres-derived source tables and sensitive-column constraints.
- `databricks_native_ingest_judgment.md` - establishes native Databricks Jobs, Spark, Delta, and Unity Catalog as the preferred operational path.
