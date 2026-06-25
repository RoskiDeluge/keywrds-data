---
title: DO Postgres -> Databricks / Unity Catalog Egress Exploration
status: exploratory
---

# DO Postgres -> Databricks / Unity Catalog Egress Exploration

## Goal

Get selected production data out of the app's database and into Databricks
so it can be analyzed (and eventually modeled) as proper tables in Unity
Catalog. This artifact scopes **what is actually possible given the current
deployment** before committing to a specific egress mechanism.

## Current deployment (grounding facts)

Pulled from `deploy/app-spec.yaml` and `keywrds/settings_production.py`:

- **Hosting:** DigitalOcean App Platform. One web service (`Dockerfile.web`)
  and one Celery worker, both small instances, `nyc` region.
- **Database:** DO **Managed Postgres, version 12**, single node
  (`db-s-dev-database`). App connects via `DATABASE_URL`
  (`${keywrds-db.DATABASE_URL}`, the in-VPC connection).
- **The connection params in the request** (host
  `...-do-user-13215853-0.b.db.ondigitalocean.com`, port `25060`,
  `sslmode=require`) are the DB's **public external endpoint**. This is the
  same cluster, exposed over the public internet with mandatory TLS.
- **Object storage:** DO **Spaces** (S3-compatible, `nyc3`), used via
  `boto3`/`django-storages` for static + media (`settings_production.py:53`).
- **Cache/broker:** DO Managed Redis 7.
- There is **no Azure resource in the stack today.**

### Correcting the framing

The request describes "grabbing the data from Azure storage and creating the
table in Unity Catalog." Today the data lives in **DO Postgres** (and DO
Spaces), not Azure. The target is confirmed **Azure Databricks**, so Azure
storage (ADLS) is the *destination* layer behind Unity Catalog managed
tables -- it is where the data **lands**, not where it currently **is**.

So the real problem is: **DO Postgres -> (staging in ADLS) -> Databricks /
Unity Catalog.**

## Decisions (from review)

- **Target:** Azure Databricks; UC managed storage is ADLS.
- **Tool to test:** `dlt` (dltHub) -- see chosen pattern C below.
- **Cadence:** one-off snapshot, run manually at first (no incremental/CDC
  yet). This materially simplifies the design -- see note under C.
- **PII:** raw PII (incl. `CustomUser` and billing data) is acceptable in the
  egressed copy; data governance will be applied **inside Databricks** as
  needed.

## What the current deployment makes possible

The single most important enabling fact: **the managed Postgres has a public,
TLS-required endpoint.** That means a Databricks notebook can connect to it
**directly** -- we are not blocked on building any export pipeline first.

Three networking realities to design around:

1. **Reachability is already there.** Port 25060 + `sslmode=require` is
   internet-reachable. A Databricks cluster with normal outbound internet can
   open a JDBC/psycopg2 connection today.
2. **Trusted Sources / firewall.** DO managed DBs can restrict inbound to
   "trusted sources." If that is (or gets) enabled, we must allowlist the
   Databricks cluster's egress. Classic Databricks clusters have **variable
   egress IPs** unless the workspace uses VNet injection / a stable NAT or
   secure cluster connectivity. This is the main networking decision.
3. **Protect the primary.** It's a single small node also serving the live
   app. Heavy analytical reads should target a **DO read replica** (DO
   supports read-only replicas) rather than the primary, or run during low
   traffic. Postgres **12 is end-of-life** upstream -- worth noting if any
   tool requires a newer server-side feature (e.g. logical-replication CDC
   ergonomics).

## Candidate patterns (notebook-runnable)

Ordered roughly simplest -> most operationally involved.

### A. Direct JDBC read in a notebook -> write to UC table
Native Spark, no extra library, no intermediary storage.

```python
df = (spark.read.format("jdbc")
      .option("url", "jdbc:postgresql://<host>:25060/keywrds-db?sslmode=require")
      .option("dbtable", "(SELECT ... FROM some_table) AS t")
      .option("user", "keywrds-db").option("password", dbutils.secrets.get(...))
      .option("driver", "org.postgresql.Driver").load())
df.write.mode("overwrite").saveAsTable("catalog.schema.some_table")
```

- **Pros:** simplest path that matches "create the proper table in UC";
  Spark infers/maps types; no Azure-storage step to manage (the data lands in
  the UC managed location automatically). Good for one-off or scheduled batch.
- **Cons:** full-table reads each run unless we add a watermark/incremental
  predicate; pulls load onto the DB (mitigate with read replica +
  `partitionColumn`/`numPartitions`).

### B. Lakehouse Federation -- register Postgres as a foreign catalog
Unity Catalog can register a **PostgreSQL connection** as a foreign catalog
and query the tables **in place**, no copy.

- **Pros:** "tables show up in Unity Catalog" with **zero egress copy**; great
  for exploration and deciding *what* is worth materializing; governed by UC
  permissions. Often the fastest way to answer "is this data useful yet?"
- **Cons:** every query hits the live DB (point at a **read replica**);
  not a substitute for a durable copy if we want history/snapshots; latency
  bound by the public connection.

### C. `dlt` pipeline -- CHOSEN
`dlt` (dltHub) is an open-source Python library you run yourself (from a
notebook, a laptop, or later a scheduled job). Its `sql_database` /
`sql_table` source reads Postgres over a normal SQLAlchemy/psycopg2
connection; its `databricks` destination uploads the data as **Parquet** to a
staging area and then runs `COPY INTO` to create/load the Unity Catalog
tables. Confirmed against the dlt docs in
[`dlt_databricks_destination_reference.md`](/Users/robertodelgado/keywrds-ai/.reffy/artifacts/dlt_databricks_destination_reference.md:1).

```python
import dlt
from dlt.sources.sql_database import sql_database

source = sql_database(
    "postgresql://keywrds-db:<pw>@<host>:25060/keywrds-db?sslmode=require",
    table_names=["..."],          # scope to the tables we want
)
pipeline = dlt.pipeline(
    pipeline_name="keywrds_pg",
    destination="databricks",      # UC table(s), staged via ADLS
    dataset_name="keywrds_raw",
)
print(pipeline.run(source, write_disposition="replace"))  # full snapshot
```

- **Pros:** matches the chosen tool; full-table snapshot is a one-liner
  (`write_disposition="replace"`); handles type mapping and table creation in
  UC; can later graduate to incremental/`merge` without changing the shape.
- **One-off snapshot does NOT need CDC.** The `wal_level=logical` /
  logical-replication concern only applies to dlt's **incremental/CDC** modes.
  A `replace` (full) load just issues normal `SELECT`s, so **PG12 is fine** and
  no DB config change is required. This is why C is cheap for our first run.
- **Staging in ADLS is unavoidable, but how much we configure varies.**
  The docs clarify two modes:
  - **Direct Load from a Databricks notebook** (chosen): dlt stages through a
    **UC managed volume** and reads auth from the notebook's runtime context --
    no external bucket keys, no `server_hostname`/`http_path` to wire by hand.
    So "no Azure-storage step" was imprecise: ADLS *is* the staging layer, we
    just don't hand-configure a bucket. Set `staging_volume_name` explicitly
    for repeatability; `keep_staged_files = false` to clean up after load.
  - **External bucket** (run anywhere): requires an ABFS `bucket_url`
    (`abfss://container@account.dfs.core.windows.net/path`) plus storage
    credentials (or a UC external location via `is_staging_external_location`
    / `staging_credentials_name`), and explicit Databricks connection +
    OAuth2/token auth. More to set up; only needed if dlt runs off-notebook.
- **Known gotcha:** inside a notebook, dltHub `dlt` collides with Databricks'
  built-in Delta Live Tables module (also `dlt`). Needs an `init.sh` rename
  workaround (or a fragile `sys.modules` purge). Budget time for this -- it's
  the most likely thing to trip on first.
- **Postgres source deps:** `sql_database` needs SQLAlchemy + a driver
  (`psycopg2`); install `dlt[databricks]` (and `dlt[az]` only if staging via an
  external Azure bucket rather than a managed volume).

If dlt's notebook setup (esp. the module conflict) proves fiddly for a
one-off, **pattern A (direct Spark JDBC -> `saveAsTable`)** above is the
no-extra-tooling fallback.

### D. Export-to-object-storage then ingest (the "Azure storage" version)
Dump tables (e.g. Parquet/CSV) to object storage, then `COPY INTO` / load
into UC. This is the pattern the original framing implied.

- **Pros:** fully decouples the DB from Databricks (export job runs in our
  infra, e.g. a Celery task or `pg_dump`/COPY to **DO Spaces** since boto3 is
  already wired up); Databricks only reads files; nice audit boundary.
- **Cons:** most moving parts; we own the export job, file formats, and
  cleanup. If staging in DO Spaces, Databricks reads cross-cloud from DO ->
  Azure compute (egress + latency); if staging in ADLS, we add an Azure leg.

## Recommendation (for the egress design that follows)

First iteration, given the decisions above:

1. **Use `dlt` for a one-off full snapshot** (`write_disposition="replace"`)
   of the scoped tables, run manually. No CDC, no `wal_level` change.
2. **Run dlt from inside an Azure Databricks notebook via Direct Load** --
   stage through a **UC managed volume** (set `staging_volume_name`) so auth
   comes from the notebook context and we avoid wiring an external bucket,
   `server_hostname`, or `http_path`. Only outbound access to the DO Postgres
   endpoint is needed beyond the notebook itself.
3. **Apply the DLT-module-conflict workaround up front** (`init.sh` rename, or
   the `sys.modules` purge) -- expect to hit this on first import in a notebook.
4. **Connect to a DO read replica, not the primary** (provision one if not
   present) so the snapshot read never competes with live app traffic.
5. **Keep credentials in Databricks secrets** -- the DO Postgres connection
   string (storage keys aren't needed under the managed-volume path).

If the notebook setup is slower to stand up than the snapshot is worth, fall
back to **pattern A (direct Spark JDBC -> `saveAsTable`)** for the very first
pull, then revisit dlt for repeatability.

Later iterations (out of scope now): graduate dlt to **incremental/`merge`**
loads once a refresh cadence is actually needed.

## Open questions (resolve before egress design)

Resolved during review: target (**Azure Databricks**), tool (**`dlt`**),
cadence (**one-off manual snapshot**), and PII (**allowed in raw; govern
inside Databricks**). See "Decisions" above. Still open:

- **Which tables / what scope?** Even with PII allowed, scope the first
  snapshot to the tables that are analytically useful rather than the whole
  schema -- keeps the first run small and the staging cost low.
  <!-- It would be useful to have the users table, a djstripe table with subscribers, a table with the Meta information for product analysis/engagment.  -->
- **Where does dlt run?** Recommendation is a Databricks notebook (Direct
  Load), but confirm the workspace allows installing dltHub `dlt` and the
  module-conflict workaround on the chosen compute (serverless 16.x vs. a
  cluster with an `init.sh`).
  <!-- Yes, it will run initially in a Notebook. -->
- **Managed volume to stage into:** which UC `staging_volume_name`
  (`catalog.schema.volume`) Direct Load uses. Only revisit an external ADLS
  bucket + credentials if we end up running dlt off-notebook.
- **Trusted Sources policy:** will we lock the DB to allowlisted sources? If
  so we need a stable egress IP from wherever dlt runs (a notebook's cluster
  has variable egress unless VNet-injected). For a manual one-off this may be
  acceptable to leave open behind strong creds + TLS.
  <!-- yes, let's leave open behind creds + TLS -->
- **Read replica:** provision a DO read replica for the snapshot read so it
  never touches the primary serving the app.
- **Secrets:** the DO Postgres connection string lives in **Databricks
  secrets**, never in notebook source. (Separately: `SECRET_KEY` is committed
  in plaintext in `deploy/app-spec.yaml` -- out of scope here but flagged.)

## Reffy References

- `martech_agentic_platform_vision.md` -- broader data/analytics ambitions
  that an egress path to Databricks would feed.
- `dev_prod_db_working_assumptions.md` -- existing assumptions about the
  prod database that constrain how aggressively we can read from it.
- `dlt_databricks_destination_reference.md` -- captured dlt Databricks
  destination docs; source for the staging, auth, and Direct Load details
  that reconciled pattern C.

## Provenance

Copied from remote Reffy workspace `keywrds-ai`, project `keywrds-ai`, artifact
`.reffy/artifacts/databricks_postgres_egress_exploration.md` on 2026-06-25.
