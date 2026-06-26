---
title: "dlt Pipeline Failure: Databricks Serverless SQL State Sync Timeout"
status: resolved
date: 2026-06-25
resolution: JDBC fallback
---

# dlt Pipeline Failure: Databricks Serverless SQL State Sync Timeout

## Summary

Attempted to run a `dlt` (dltHub) pipeline from inside an Azure Databricks
**serverless notebook** (runtime 16.x) using **Direct Load** mode (UC managed
volume staging). The pipeline failed at the `sync` step — dlt could not
establish a connection back to the Databricks SQL endpoint to restore/persist
pipeline state.

## Environment

| Component | Value |
| --- | --- |
| Databricks compute | Serverless interactive cluster (CPU) |
| Runtime | 16.x (serverless) |
| Cloud | Azure (West US 2) |
| dlt version | installed via `pip install "dlt[databricks,sql_database]"` (latest at 2026-06-25) |
| Source | DigitalOcean Managed Postgres 12, public endpoint, port 25060, sslmode=require |
| Destination | `databricks` (Direct Load, UC managed volume) |
| Target catalog | `keywrds-ga4` (hyphenated name, requires backtick quoting) |
| Write disposition | `replace` (full snapshot) |

## What Succeeded

1. **`%pip install "dlt[databricks,sql_database]" psycopg2-binary`** — installed
   cleanly on serverless.
2. **Module conflict workaround** — stripping the first `sys.meta_path` hook
   after pip-triggered restart allowed `import dlt` to resolve to dltHub's
   package (not Databricks' built-in Delta Live Tables module).
3. **Source connection** — `sql_database(PG_CONN, table_names=[...])` connected
   to the DO Postgres endpoint successfully (confirmed by cell execution
   completing without error and returning resource objects).
4. **Schema creation** — `CREATE SCHEMA IF NOT EXISTS \`keywrds-ga4\`.\`production\``
   succeeded.

## What Failed

### Error

```
PipelineStepFailed: Pipeline execution failed at `step=sync` with exception:

<class 'databricks.sql.exc.RequestError'>
Error during request to server. Retry request would exceed Retry policy max retry duration of 900.0 seconds
```

Trace ID: `00-8c4e0701de692f26eb5eebe15d295ea7-bac9bd936cde4f1e-00`

### Failure Point

The failure occurs at `pipeline._sync_destination()` → `pipeline._restore_state_from_destination()` — **before any data is loaded**. dlt is
trying to connect to Databricks SQL (via `databricks-sql-connector`) to read
its internal pipeline state table and timed out after retrying for 900 seconds.

### Pipeline Configuration

```python
from dlt.destinations import databricks

bricks = databricks(credentials={"catalog": "keywrds-ga4"})

pipeline = dlt.pipeline(
    pipeline_name="keywrds_pg_raw",
    dataset_name="production",
    destination=bricks,
)

load_info = pipeline.run(source, write_disposition="replace")
```

No explicit `server_hostname` or `http_path` was provided — relying on dlt's
documented behavior of deriving connection from the notebook cluster context
(Direct Load mode).

### Root Cause Hypothesis

dlt's `databricks-sql-connector` usage appears incompatible with the serverless
notebook execution context. Possible reasons:

1. **Serverless compute does not expose a traditional JDBC/ODBC endpoint** that
   `databricks-sql-connector` can discover from the notebook's runtime context
   (no `DATABRICKS_SERVER_HOSTNAME` / `DATABRICKS_HTTP_PATH` injected, or the
   values don't route correctly from within the serverless environment).

2. **SQL warehouse discovery fallback fails** — dlt docs say it falls back to
   `DATABRICKS_WAREHOUSE_ID` or "first available SQL warehouse." If no SQL
   warehouse is running/accessible, the connection attempt hangs until the 900s
   retry cap.

3. **Network loopback issue** — the serverless cluster may not be able to reach
   its own workspace's SQL endpoint from within the execution container (firewall
   or routing limitation specific to serverless infra).

4. **Hyphenated catalog name** — while unlikely to cause a *connection* timeout,
   the catalog name `keywrds-ga4` may not be properly escaped in dlt's internal
   queries, though this would more likely produce a parse error than a timeout.

## Questions for dlt Team

1. Is Direct Load mode tested/supported on **Databricks Serverless** (16.x)
   notebooks specifically? The docs mention notebook support but don't
   distinguish classic clusters vs. serverless.

2. What does dlt use internally to derive `server_hostname` / `http_path` when
   running in-notebook with no explicit credentials? Is it reading env vars,
   notebook context APIs, or the Spark conf?

3. Is there a way to force dlt to use the **notebook's own attached compute**
   for SQL execution (via Spark) rather than opening a separate
   `databricks-sql-connector` connection? On serverless, the notebook already
   has a running SQL execution context.

4. Would providing explicit `server_hostname` + `http_path` pointing to a SQL
   warehouse (rather than relying on auto-discovery) resolve the timeout? If so,
   this should be documented as required for serverless.

5. Is the 900-second retry cap configurable? For debugging, a faster failure
   would have saved ~14 minutes of wait time.

## Workaround Applied

Fell back to **direct Spark JDBC** (`spark.read.format("jdbc")` →
`df.write.saveAsTable()`), which worked immediately with no issues:

```python
from urllib.parse import urlparse

parsed = urlparse(PG_CONN)
jdbc_url = f"jdbc:postgresql://{parsed.hostname}:{parsed.port}{parsed.path}?sslmode=require"

df = (spark.read.format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", "(SELECT * FROM users_customuser) AS t")
    .option("user", parsed.username)
    .option("password", parsed.password)
    .option("driver", "org.postgresql.Driver")
    .load()
    .drop("password")
)
df.write.mode("overwrite").saveAsTable("`keywrds-ga4`.`production`.`tbl__raw__production__users_customuser`")
```

This confirms:
- Outbound network to DO Postgres is fine (not a firewall issue).
- Writing to Unity Catalog from serverless works (Spark's native UC integration).
- The failure is isolated to dlt's `databricks-sql-connector` connection path.

## Result

Both tables loaded successfully via JDBC fallback:
- `keywrds-ga4.production.tbl__raw__production__users_customuser` — 16,097 rows
- `keywrds-ga4.production.tbl__raw__production__djstripe_subscription` — 135 rows

## Reffy References

- `databricks_postgres_egress_exploration.md` — original egress design that
  chose dlt and identified JDBC as the fallback.
- `dlt_databricks_destination_reference.md` — Direct Load docs and module
  conflict workaround.
- `databricks_initial_table_scope.md` — table scope for the ingest.

## Notebook

The notebook with both the failed dlt attempt and successful JDBC fallback is at:
`/Users/roberto@keywrds.ai/keywrds-data/raw_ingest__postgres_one_off`
