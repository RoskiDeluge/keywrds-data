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
| Target catalog | `keywrds` |
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
4. **Schema creation** — `CREATE SCHEMA IF NOT EXISTS \`keywrds\`.\`production\``
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

bricks = databricks(credentials={"catalog": "keywrds"})

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

4. **Catalog quoting** — now lower probability. The catalog was renamed from
   `keywrds-ga4` to `keywrds`, removing the original hyphenated-identifier
   concern. Even before the rename, a quoting issue would more likely produce
   a parse error than a connection timeout.

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
df.write.mode("overwrite").saveAsTable("`keywrds`.`production`.`tbl__raw__production__users_customuser`")
```

This confirms:
- Outbound network to DO Postgres is fine (not a firewall issue).
- Writing to Unity Catalog from serverless works (Spark's native UC integration).
- The failure is isolated to dlt's `databricks-sql-connector` connection path.

## Result

Both tables loaded successfully via JDBC fallback:
- `keywrds.production.tbl__raw__production__users_customuser` — 16,097 rows
- `keywrds.production.tbl__raw__production__djstripe_subscription` — 135 rows

## Reffy References

- `databricks_postgres_egress_exploration.md` — original egress design that
  chose dlt and identified JDBC as the fallback.
- `dlt_databricks_destination_reference.md` — Direct Load docs and module
  conflict workaround.
- `databricks_initial_table_scope.md` — table scope for the ingest.

## Notebook

The notebook with both the failed dlt attempt and successful JDBC fallback is at:
`/Users/roberto@keywrds.ai/keywrds-data/raw_ingest__postgres_one_off`

## Partial error trace: 

PipelineStepFailed: Pipeline execution failed at `step=sync` with exception:


Error during request to server. Retry request would exceed Retry policy max retry duration of 900.0 seconds
[Trace ID: 00-8c4e0701de692f26eb5eebe15d295ea7-bac9bd936cde4f1e-00]
File /local_disk0/.ephemeral_nfs/envs/pythonEnv-5549ee03-2980-43f5-8a03-bef6db889712/lib/python3.12/site-packages/dlt/pipeline/pipeline.py:832, in Pipeline._sync_destination(self, destination, staging, dataset_name)
    830 restored_schemas: Sequence[Schema] = None
--> 832 remote_state = self._restore_state_from_destination()
    834 # if remote state is newer or same
    835 # TODO: check if remote_state["_state_version"] is not in 10 recent version. then we know remote is newer.
File /local_disk0/.ephemeral_nfs/envs/pythonEnv-5549ee03-2980-43f5-8a03-bef6db889712/lib/python3.12/site-packages/dlt/pipeline/pipeline.py:938, in Pipeline._sync_destination(self, destination, staging, dataset_name)
    936     self._save_state(state)
    937 except (Exception, KeyboardInterrupt) as ex:
--> 938     raise PipelineStepFailed(self, "sync", None, ex, None) from ex

## Upstream fix analysis for dlt

The partial trace makes the failure more specific than "Databricks Direct Load
does not work." The pipeline fails in the **sync** step before extraction,
normalization, staging, or `COPY INTO`. That points at the destination SQL
client that dlt uses to read/write internal pipeline state, not at Postgres
connectivity or Unity Catalog table creation.

### Relevant dlt code path to inspect

Likely files in the open source `dlt` repo:

- `dlt/pipeline/pipeline.py`
  - `_sync_destination()`
  - `_restore_state_from_destination()`
  - call path into `load_pipeline_state_from_destination(...)`
- `dlt/destinations/impl/databricks/configuration.py`
  - `DatabricksCredentials.on_resolved()`
  - derives `server_hostname`, `http_path`, and auth from Databricks notebook
    context / SDK config / warehouse discovery.
- `dlt/destinations/impl/databricks/sql_client.py`
  - `DatabricksSqlClient.open_connection()`
  - always opens a `databricks.sql.connect(...)` DB-API connection.
- `dlt/destinations/impl/databricks/databricks.py`
  - Direct Load managed-volume handling and `COPY INTO` execution.

The current implementation appears to treat "running in a Databricks notebook"
as enough to build a Databricks SQL connector connection:

```text
notebook context -> workspace host + cluster/workspace id -> http_path
fallback -> SQL warehouse discovery
open -> databricks.sql.connect(...)
```

That assumption is probably too broad for **serverless notebooks**. In this
case, the notebook's Spark/UC path works, but the DB-API SQL connector path
hangs until the connector retry policy gives up.

### Working hypothesis

The generated or discovered Databricks SQL connection parameters are syntactically
valid enough to start a connector request, but not operationally valid for the
serverless notebook context. The important distinction:

- **Spark SQL in the attached serverless notebook works.**
- **`databricks-sql-connector` from inside that notebook does not complete.**

So the bug is likely one of these:

1. dlt derives a cluster-style `http_path` for a serverless notebook even
   though that path is not usable by `databricks-sql-connector`.
2. dlt falls back to the first visible SQL warehouse, but that warehouse is not
   running, inaccessible, or unsuitable, causing a long connector retry instead
   of a fast configuration error.
3. dlt has no preflight validation for the resolved Databricks connection, so
   the first real failure appears deep inside pipeline state sync after a
   900-second retry window.

The catalog was renamed from `keywrds-ga4` to `keywrds`, which removes the
hyphenated-identifier concern from the current reproduction path. If catalog
quoting were the issue, Spark/SQL would likely raise a parse or identifier
error after a connection opens. The observed failure is connection/request
timeout before any state query result is available.

### Minimal upstream fix

The smallest useful fix is better **serverless detection + faster failure** in
the Databricks credential/client path.

Proposal:

1. In `DatabricksCredentials.on_resolved()`, when dlt is deriving `http_path`
   from notebook context, detect serverless compute separately from classic
   clusters.
2. If the notebook context is serverless and no explicit `http_path` or
   `DATABRICKS_WAREHOUSE_ID` is configured, do **not** silently construct a
   cluster-style SQL connector path and wait for connector retries.
3. Raise a `ConfigurationValueError` with an actionable message:

```text
Databricks Direct Load could not derive a SQL connector endpoint for this
serverless notebook. Provide explicit `server_hostname` and `http_path` for a
SQL warehouse, set `DATABRICKS_WAREHOUSE_ID`, or use the Spark/JDBC fallback.
```

4. Add a short connection preflight before pipeline state restore, or make
   `DatabricksSqlClient.open_connection()` wrap connector request timeouts with
   a Databricks-specific hint that includes:
   - resolved `server_hostname`
   - resolved `http_path` shape (redacted enough for logs)
   - whether auth came from notebook context, SDK default auth, or explicit
     token/OAuth
   - whether a warehouse fallback was used

This would not make serverless Direct Load work by itself, but it would turn a
14-15 minute timeout into an immediate, actionable configuration error.

### Better upstream fix

The more complete fix is a Databricks notebook-native SQL client path for
Direct Load.

If dlt is running **inside a Databricks notebook**, especially on serverless,
it already has a working Spark execution context. For Direct Load, dlt could
execute the state-sync SQL, schema DDL, `CREATE VOLUME`, `PUT`/volume staging
commands where applicable, and `COPY INTO` through the notebook's Spark SQL
session instead of always opening a separate `databricks-sql-connector`
connection.

Possible shape:

```python
bricks = databricks(
    credentials={"catalog": "keywrds"},
    use_notebook_spark_sql=True,  # explicit at first; auto-detect later
)
```

Implementation sketch:

1. Add a Databricks SQL client variant, for example
   `DatabricksSparkSqlClient`, implementing the subset of `SqlClientBase`
   needed by destination state sync and load jobs.
2. Use `SparkSession.getActiveSession()` or the Databricks notebook runtime to
   execute SQL via `spark.sql(...)`.
3. Convert result rows into the cursor shape expected by dlt state-sync helpers.
4. Keep the existing `DatabricksSqlClient` as the default for non-notebook
   execution and SQL warehouse execution.
5. Select the Spark client only when:
   - running in a Databricks notebook,
   - destination is Databricks,
   - no explicit `server_hostname` / `http_path` was supplied, and
   - Direct Load / managed-volume mode is requested.

This matches the successful workaround: serverless Spark can already create
schemas and write UC tables. The missing piece is letting dlt use that same
working execution path for its own state-sync and destination SQL operations.

### Why the better fix is probably worth it

Direct Load is documented as a notebook-friendly path, but the current behavior
still depends on opening a second SQL connector connection from inside the
notebook. That is surprising to users because "the notebook can run SQL" feels
equivalent to "dlt can run SQL." On serverless, those are apparently different
execution paths.

A notebook-native client would make dlt's Direct Load semantics line up with
the user's mental model:

- source extraction runs in notebook Python,
- staging/loading SQL runs through the attached Databricks runtime,
- auth comes from the current workspace context,
- no separate SQL warehouse or connector endpoint is needed for the simplest
  notebook case.

### Suggested issue/PR framing

Title:

```text
Databricks Direct Load from serverless notebook times out during pipeline state sync
```

Problem statement:

```text
When running dlt's Databricks destination from an Azure Databricks serverless
notebook with Direct Load and no explicit `server_hostname`/`http_path`,
pipeline execution fails at `step=sync` before any data load. Spark SQL and UC
writes work from the same notebook, but dlt's internal `databricks-sql-connector`
path retries for 900 seconds and then raises RequestError.
```

Proposed initial PR:

```text
Detect serverless notebook contexts during Databricks credential resolution and
fail fast with a clear message unless an explicit SQL warehouse endpoint is
configured. Add debug logging for resolved Databricks SQL connection source.
```

Follow-up PR:

```text
Add a notebook-native Spark SQL client for Databricks Direct Load so serverless
notebooks can run destination state sync and load SQL without a separate
databricks-sql-connector connection.
```

### Test plan for dlt clone

Unit tests:

1. Mock Databricks SDK notebook context that returns a classic cluster id and
   workspace id. Assert existing cluster-style `http_path` behavior remains.
2. Mock serverless notebook context. Assert dlt does not derive an unusable
   cluster-style connector path without explicit warehouse config.
3. Mock no notebook context + warehouse id configured. Assert warehouse
   discovery still resolves `server_hostname` and `http_path`.
4. Mock `databricks.sql.connect` raising `RequestError` / timeout from
   `open_connection()`. Assert dlt wraps it with a clear Databricks Direct Load
   diagnostic instead of surfacing only a generic sync failure.

Integration test, if dlt maintainers have Databricks CI:

1. Serverless notebook, Direct Load, managed volume, no explicit SQL warehouse.
2. Expected behavior for minimal fix: fast configuration error with documented
   remediation.
3. Expected behavior for better fix: pipeline state sync and a tiny one-table
   load succeed through notebook Spark SQL.

### Local validation path before proposing upstream

In the cloned dlt project, first reproduce with a tiny destination-only test:

```python
from dlt.destinations import databricks
import dlt

bricks = databricks(credentials={"catalog": "keywrds"})
pipeline = dlt.pipeline(
    pipeline_name="serverless_state_sync_probe",
    dataset_name="production",
    destination=bricks,
)

# Even an empty/tiny source should trigger destination sync before load.
pipeline.run([{"id": 1}], table_name="dlt_serverless_probe", write_disposition="replace")
```

Then instrument/log:

```text
DatabricksCredentials.server_hostname
DatabricksCredentials.http_path
DatabricksCredentials.auth source
whether warehouse fallback ran
DatabricksSqlClient.open_connection() elapsed time
```

If explicit warehouse credentials make the probe pass, the first PR should be
fast-fail + docs. If explicit warehouse credentials still hang from serverless,
the stronger Spark SQL client path becomes the main fix.
