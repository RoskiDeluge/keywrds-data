# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Title and Overview
# MAGIC %md
# MAGIC # Raw Ingest: DO Postgres → Unity Catalog (One-Off Snapshot)
# MAGIC
# MAGIC One-off full snapshot of **2 tables** from DigitalOcean Managed Postgres into `keywrds.production`:
# MAGIC
# MAGIC | Source Table | Target Table |
# MAGIC | --- | --- |
# MAGIC | `users_customuser` | `keywrds.production.tbl__raw__production__users_customuser` |
# MAGIC | `djstripe_subscription` | `keywrds.production.tbl__raw__production__djstripe_subscription` |
# MAGIC
# MAGIC **Approach:** `dlt` (dltHub) Direct Load — stages through a UC managed volume, auth from notebook context.  
# MAGIC **Disposition:** `replace` (full snapshot, no incremental/CDC).  
# MAGIC **Note:** JDBC fallback at bottom if dlt module conflict is unresolvable on this compute.

# COMMAND ----------

# DBTITLE 1,Prerequisites
# MAGIC %md
# MAGIC ## Prerequisites
# MAGIC
# MAGIC **1. Databricks Secret Scope** — a scope `keywrds-data` with key `pg-connection-string`:
# MAGIC
# MAGIC ```
# MAGIC postgresql://<user>:<password>@<host>:25060/<database>?sslmode=require
# MAGIC ```
# MAGIC
# MAGIC CLI commands to create:
# MAGIC ```bash
# MAGIC databricks secrets create-scope keywrds-data
# MAGIC databricks secrets put-secret keywrds-data pg-connection-string
# MAGIC ```
# MAGIC
# MAGIC **2. Unity Catalog** — catalog `keywrds` and schema `production` must exist (or the running user needs `CREATE CATALOG` / `CREATE SCHEMA` privileges; Cell 6 handles creation).
# MAGIC
# MAGIC **3. Network** — the DO Postgres public endpoint (port 25060, TLS) must be reachable from this compute. Serverless has outbound internet by default.

# COMMAND ----------

# DBTITLE 1,Install dependencies
# MAGIC %pip install "dlt[databricks,sql_database]" psycopg2-binary --quiet

# COMMAND ----------

# DBTITLE 1,Module conflict workaround and imports
import sys

# Strip the Databricks DLT meta_path hook that shadows dltHub's `dlt` module.
# On serverless (16.x), the hook is always the first entry after a pip-triggered restart.
_original_hook = sys.meta_path.pop(0)

import dlt
from dlt.sources.sql_database import sql_database
from dlt.destinations import databricks

# Restore the hook so other Databricks internals continue to work
sys.meta_path.insert(0, _original_hook)

# COMMAND ----------

# DBTITLE 1,Configuration
# Retrieve Postgres connection string from secrets
PG_CONN = dbutils.secrets.get(scope="keywrds-data", key="pg-connection-string")

# Target naming
CATALOG = "keywrds"
SCHEMA = "production"
TABLE_PREFIX = "tbl__raw__production__"

SOURCE_TABLES = ["users_customuser", "djstripe_subscription"]

# COMMAND ----------

# DBTITLE 1,Ensure catalog and schema exist
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# COMMAND ----------

# DBTITLE 1,Define source and apply transformations
# Create the sql_database source scoped to our two tables
source = sql_database(
    PG_CONN,
    table_names=SOURCE_TABLES,
)

# Drop password hash from users_customuser — no reason to egress credential hashes
source.users_customuser.add_map(
    lambda row: {k: v for k, v in row.items() if k != "password"}
)

# Apply custom table naming convention
source.users_customuser.apply_hints(table_name=f"{TABLE_PREFIX}users_customuser")
source.djstripe_subscription.apply_hints(table_name=f"{TABLE_PREFIX}djstripe_subscription")

# COMMAND ----------

# DBTITLE 1,Define pipeline and run
# Direct Load: dlt uses notebook context for auth, default managed volume for staging
bricks = databricks(credentials={"catalog": CATALOG})

pipeline = dlt.pipeline(
    pipeline_name="keywrds_pg_raw",
    dataset_name=SCHEMA,
    destination=bricks,
)

# Full snapshot (one-off)
load_info = pipeline.run(source, write_disposition="replace")
print(load_info)

# COMMAND ----------

# DBTITLE 1,Verification
print("=== Loaded Tables ===")
for tbl in SOURCE_TABLES:
    fqn = f"{CATALOG}.{SCHEMA}.{TABLE_PREFIX}{tbl}"
    count = spark.table(fqn).count()
    print(f"{CATALOG}.{SCHEMA}.{TABLE_PREFIX}{tbl}: {count} rows")

# Quick preview
display(spark.table(f"{CATALOG}.{SCHEMA}.{TABLE_PREFIX}users_customuser").limit(5))
display(spark.table(f"{CATALOG}.{SCHEMA}.{TABLE_PREFIX}djstripe_subscription").limit(5))

# COMMAND ----------

# DBTITLE 1,Appendix - JDBC Fallback
# MAGIC %md
# MAGIC ---
# MAGIC ## Appendix: Fallback — Direct Spark JDBC
# MAGIC
# MAGIC If the dlt module conflict is unresolvable on this compute, the cell below provides a pure-Spark JDBC alternative.  
# MAGIC No pip installs needed, no module conflicts — built-in Spark JDBC driver.

# COMMAND ----------

# DBTITLE 1,JDBC fallback (commented out)
# --- JDBC APPROACH (dlt failed on Databricks SQL state sync) ---
from urllib.parse import urlparse

# Parse connection string from the existing secret
parsed = urlparse(PG_CONN)
jdbc_url = f"jdbc:postgresql://{parsed.hostname}:{parsed.port}{parsed.path}?sslmode=require"
pg_user = parsed.username
pg_password = parsed.password

# users_customuser (drop password column)
df_users = (spark.read.format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", "(SELECT * FROM users_customuser) AS t")
    .option("user", pg_user)
    .option("password", pg_password)
    .option("driver", "org.postgresql.Driver")
    .load()
    .drop("password")
)
df_users.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.{TABLE_PREFIX}users_customuser")
print(f"✓ {TABLE_PREFIX}users_customuser written")

# djstripe_subscription
df_subs = (spark.read.format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", "(SELECT * FROM djstripe_subscription) AS t")
    .option("user", pg_user)
    .option("password", pg_password)
    .option("driver", "org.postgresql.Driver")
    .load()
)
df_subs.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.{TABLE_PREFIX}djstripe_subscription")
print(f"✓ {TABLE_PREFIX}djstripe_subscription written")

print("\nJDBC ingest complete.")
