---
title: dlt -> Databricks Destination (Reference)
status: reference
source: https://dlthub.com/docs/dlt-ecosystem/destinations/databricks.md
retrieved: 2026-06-23
---

<!--
Reference artifact: condensed capture of the official dlt Databricks
destination docs, imported for internal use while designing the
DO Postgres -> Databricks egress. See databricks_postgres_egress_exploration.md
for how this informs the chosen `dlt` one-off-snapshot approach. Sections
most relevant to our case (Azure Blob/ADLS staging + notebook Direct Load)
are kept in full; peripheral features (Zerobus, dbt, exhaustive adapter
examples) are summarized. Verify against the live doc before relying on
exact option names.
-->

# dlt -> Databricks Destination (Reference)

The Databricks destination loads data into **Delta** (default) or **Iceberg**
tables, accessible via **Unity Catalog**. Data is staged to cloud storage as
**Parquet** (default) or JSONL, then ingested with `COPY INTO`.

Two ways to run:
1. Provide credentials for both Databricks **and** a cloud storage bucket
   (run anywhere).
2. Run **directly inside a Databricks notebook** -- no explicit credentials;
   dlt uses the notebook/runtime context. (See **Direct Load** below -- this is
   the path that fits our one-off, notebook-run snapshot.)

## Install

```sh
pip install "dlt[databricks]"     # core + Databricks dbapi client
pip install "dlt[az]"             # add when staging via Azure Blob / ADLS
```

## Destination capabilities (selected)

| Feature | Value |
|---|---|
| Preferred loader / staging file format | parquet |
| Supported loader formats | jsonl, parquet, model |
| Supported table formats | delta, iceberg |
| Merge strategies | delete-insert, upsert, scd2, insert-only |
| Replace strategies | truncate-and-insert, insert-from-staging, staging-optimized |
| Case-sensitive identifiers | False |
| tz-aware & naive datetime | both supported |

All write dispositions are supported (`replace` = our full snapshot).

## Workspace prerequisites (Azure)

- A Databricks workspace (Premium tier for Unity Catalog) with a UC metastore.
- A **Gen 2 Azure storage account** (hierarchical namespace enabled) + a
  container -- used as the datastore behind the catalog and for staging.
- An **Access Connector for Azure Databricks** granted **Storage Blob Data
  Contributor** on the container (via Managed Identity).
- In Databricks Catalog: add a **Storage Credential** (the Access Connector
  resource ID), an **External Location**
  (`abfss://<container>@<storage_account>.dfs.core.windows.net/<path>`), then
  **create the catalog** pointing at that location.

## Authentication

Two supported methods (set in `.dlt/secrets.toml`, env vars, or by reassigning
env vars in code -- never hardcode secrets):

**OAuth2 M2M (recommended)** -- service principal `client_id` / `client_secret`:
```toml
[destination.databricks.credentials]
server_hostname = "MY_DATABRICKS.azuredatabricks.net"
http_path = "/sql/1.0/warehouses/12345"
catalog = "my_catalog"
client_id = "XXX"
client_secret = "XXX"
```

**Access token** -- developer token (may be deprecated by Databricks later):
```toml
[destination.databricks.credentials]
server_hostname = "MY_DATABRICKS.azuredatabricks.net"
http_path = "/sql/1.0/warehouses/12345"
catalog = "my_catalog"
access_token = "XXX"
```

Env-var form uses the `DESTINATION__DATABRICKS__CREDENTIALS__<FIELD>` prefix.
Find `server_hostname` / `http_path` under SQL Warehouses -> your warehouse ->
Connection details.

**Default credentials:** if no auth is configured, dlt pulls authorization
from the Databricks workspace context (notebook runtime, or `DATABRICKS_TOKEN`
/ `DATABRICKS_HOST` env vars). When `server_hostname`/`http_path` are omitted,
dlt derives them: (1) from the **notebook cluster context** first (uses the
notebook's own attached cluster, no SQL warehouse needed), or (2) falls back
to **SQL warehouse discovery** (`DATABRICKS_WAREHOUSE_ID` or first available).

## Loader setup (CLI scaffold)

```sh
dlt init chess databricks          # scaffold a pipeline targeting databricks
pip install -r requirements.txt    # installs dlt[databricks]
# then fill .dlt/secrets.toml with credentials + catalog
```

## Direct Load (Databricks Managed Volumes) -- relevant to us

dlt can run from a **Databricks notebook with no external staging**, using a
**managed volume** as the temporary staging area. It also works outside
Databricks if you pass `server_hostname`, `http_path`, `catalog`, and auth.

```py
import dlt
from dlt.destinations import databricks

# Fully-qualified managed volume (recommended for production; assumed to exist)
staging_volume_name = "dlt_ci.dlt_tests_shared.static_volume"

bricks = databricks(
    credentials={"catalog": "dlt_ci"},
    staging_volume_name=staging_volume_name,
)

pipeline = dlt.pipeline(
    pipeline_name="rest_api_example",
    dataset_name="rest_api_data",
    destination=bricks,
)
load_info = pipeline.run(source)   # our source = sql_database(postgres...)
```

- If no `staging_volume_name` is given, dlt creates a **default volume**.
- For production, set `staging_volume_name` explicitly.
- Delete staged files right after load with:
  ```toml
  [destination.databricks]
  keep_staged_files = false
  ```
- **Module conflict warning:** inside Databricks notebooks, dltHub's `dlt`
  collides with Databricks' built-in Delta Live Tables (also `dlt`). See
  Troubleshooting below -- this is the most likely setup snag.

## Staging support (external bucket option)

If not using Direct Load volumes, configure an S3 / Azure Blob / GCS bucket.
dlt uploads Parquet to the bucket, then `COPY INTO` loads it.

**Azure Blob / ADLS** (requires `dlt[az]`). Databricks wants **ABFS** URLs:
```toml
[destination.filesystem]
bucket_url = "abfss://container_name@storage_account_name.dfs.core.windows.net/path"

[destination.filesystem.credentials]
azure_storage_account_name = "XXX"
azure_storage_account_key  = "XXX"
```
(dlt can adapt `az://container/path` but ABFS is recommended.)

**Use external locations / stored credentials** instead of forwarding bucket
keys to `COPY INTO` (preferred with the UC external location we set up):
```toml
[destination.databricks]
is_staging_external_location = true        # use the configured external location
# or:
staging_credentials_name = "credential_x"  # named Databricks credential
```

S3 and GCS are also supported (GCS requires a named credential).

## File format notes

- **Parquet** (default) -- best performance, broadest type support. Use it.
- **JSONL** limitations: no `decimal`, `json`, `date`, `binary`; no `bigint`
  with precision.

## Supported hints (Unity Catalog)

Table: `description`/`table_comment`. Column: `primary_key`, `references`
(both need `create_indexes = true`), `description`, `not_null`, `cluster`.
The `databricks_adapter(resource, ...)` function adds Databricks-specific
table/column hints -- comments, tags, `cluster`/`partition` (mutually
exclusive), `table_format` (`DELTA`/`ICEBERG`), `table_properties`
(Delta optimization TBLPROPERTIES like `delta.autoOptimize.optimizeWrite`).

## Other capabilities (summarized)

- **dbt** integration via `dbt-databricks`.
- **dlt state sync** fully supported.
- Connection identifies itself to Databricks as `dltHub_dlt` (user agent).
- **Zerobus** ingestion (`insert_api = "zerobus"`): alternative to `COPY INTO`,
  **`append`-only**, at-least-once (possible duplicates), Linux/Windows only
  (no macOS wheels). Not relevant to our `replace` snapshot.

## Troubleshooting -- DLT module name conflict (notebooks)

dltHub `dlt` clashes with Databricks' built-in Delta Live Tables module.

- **Serverless (16.x):** `%restart_python`, then strip the first `sys.meta_path`
  hook before `import dlt`, restore it after.
- **Cluster:** add an `init.sh` that renames the built-in module to
  `dlt_dbricks` (moves `/databricks/spark/python/dlt`, `sed`-rewrites imports,
  patches `DeltaLiveTablesHook.py`) and `pip install dlt`. Attach via cluster
  Advanced Options -> Init Scripts. Note the hook file path moves between
  runtimes (16.4 LTS vs 15.4 LTS differ).
- A fragile in-notebook fallback purges half-initialized DLT modules from
  `sys.modules`; the `init.sh` approach is preferred.

## Relevance to our egress design

See [`databricks_postgres_egress_exploration.md`](/Users/robertodelgado/keywrds-ai/.reffy/artifacts/databricks_postgres_egress_exploration.md:1).
Key takeaways for our one-off snapshot:
- **Direct Load from a notebook** removes the need to wire external bucket
  credentials -- strongest fit for "run manually inside Azure Databricks."
- Either way a **staging layer in ADLS** is involved (managed volume or an
  external ABFS location); the UC external location set up during workspace
  prep is what `is_staging_external_location` / `staging_credentials_name`
  would reference.
- Use **Parquet** + `write_disposition="replace"`; no Zerobus, no CDC.
- Budget time for the **DLT-module-conflict** workaround when running in a
  notebook -- likely the first thing to trip on.

## Provenance

Copied from remote Reffy workspace `keywrds-ai`, project `keywrds-ai`, artifact
`.reffy/artifacts/dlt_databricks_destination_reference.md` on 2026-06-25.
