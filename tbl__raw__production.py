# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Title and Overview
# MAGIC %md
# MAGIC # Raw Ingest: DO Postgres → Unity Catalog 
# MAGIC
# MAGIC One-off full snapshot of **2 tables** from DigitalOcean Managed Postgres into `keywrds.production`:
# MAGIC
# MAGIC | Source Table | Target Table |
# MAGIC | --- | --- |
# MAGIC | `users_customuser` | `keywrds.production.tbl__raw__production__users_customuser` |
# MAGIC | `djstripe_subscription` | `keywrds.production.tbl__raw__production__djstripe_subscription` |
# MAGIC
# MAGIC **Approach:** Direct Spark JDBC → `saveAsTable` (no extra dependencies).  
# MAGIC **Disposition:** `replace` (full snapshot, no incremental/CDC).

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
# MAGIC **2. Unity Catalog** — catalog `keywrds` and schema `production` must exist (or the running user needs `CREATE SCHEMA` privileges; the next cell handles creation).
# MAGIC
# MAGIC **3. Network** — the DO Postgres public endpoint (port 25060, TLS) must be reachable from this compute. Serverless has outbound internet by default.

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

# DBTITLE 1,JDBC fallback (commented out)
# --- Ingest: DO Postgres → Unity Catalog via Spark JDBC ---
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
