# Keywrds.ai - Data

## Databricks environments

Development work is isolated in the `dbw_sql_dev_westus2` catalog:

| Schema | Purpose |
| --- | --- |
| `development` | Free-form experiments and temporary work |
| `raw` | Minimally transformed source inputs |
| `refactored` | Cleaned and conformed models |
| `primary` | Validated release candidates |

Approved model definitions are deployed to the `keywrds-data` workspace and
recomputed into `keywrds_data.production`. Development tables are not copied
directly into production.

Human members of `keywrds-data-prod-users` have read-only production data
access. Automated publication runs as the `keywrds-data-prod-publisher`
service principal, whose write privileges are restricted to the production
schema.

## Bundle targets

The repository uses a Databricks Declarative Automation Bundle:

```bash
# Local development validation
DATABRICKS_AUTH_STORAGE=plaintext databricks bundle validate --strict \
  --target dev --profile keywrds-data-dev

# Local production validation as an administrator
DATABRICKS_AUTH_STORAGE=plaintext databricks bundle validate --strict \
  --target prod --profile kewyrds-data-prod
```

Environment-specific code should use `${var.catalog}` and `${var.schema}` in
bundle resource definitions. Add approved jobs or pipelines under
`resources/` using the `<name>.<resource_type>.yml` naming convention.

## Production deployment

Production deployment is manual through the GitHub Actions workflow
`Deploy approved models to production`. The workflow uses GitHub OIDC and
Databricks OAuth federation, so it stores no Databricks token or client secret.

The GitHub `production` environment provides these non-secret variables:

- `DATABRICKS_HOST`: `https://adb-7405613586421163.3.azuredatabricks.net`
- `DATABRICKS_CLIENT_ID`: the application ID of
  `keywrds-data-prod-publisher`

The Databricks federation policy accepts only the OIDC subject
`repo:RoskiDeluge/keywrds-data:environment:production`.
