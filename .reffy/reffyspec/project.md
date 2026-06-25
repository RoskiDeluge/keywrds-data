# Project Context

## Purpose
This repository stores data exploration and ingestion notebooks for Keywrds.ai analytics and billing data. Its current focus is:

- Materializing raw Stripe customer and subscription Parquet exports into Databricks tables.
- Exploring GA4 event exports locally with pandas and SQLite.
- Preserving lightweight project guidance and future planning context through Reffy/ReffySpec.

## Tech Stack
- Jupyter notebooks (`.ipynb`) as the main executable artifacts.
- Databricks notebooks using Python, PySpark/Spark SQL, and Databricks notebook metadata.
- Azure Data Lake Storage paths via `abfss://`, currently under `keywrds-stripe-data@keywrdsstripedata.dfs.core.windows.net`.
- Databricks managed/external tables under the `stripe.stripe_data` schema.
- Local Python data exploration with `pandas` and the standard-library `sqlite3` module.
- CSV extracts for GA4 exploration; local SQLite databases for ad hoc analysis.
- Reffy/ReffySpec for repository-local context, planning scaffolds, and capability specs.

## Project Conventions

### Code Style
- Keep notebooks small and task-focused. Prefer one notebook per source or analysis workflow.
- Use clear table names that include source, layer, and dataset, such as `tbl__stripe__initial_raw_subscriptions_data`.
- Keep SQL readable with uppercase SQL keywords where practical and explicit schema/table names.
- Prefer explicit Spark read options such as `recursiveFileLookup` and `pathGlobFilter` when reading nested exports.
- Avoid committing generated local data, databases, virtual environments, logs, or notebook checkpoints. `.gitignore` excludes `*.csv`, `*.json`, `*.db`, virtual environments, and `.ipynb_checkpoints`.
- Treat committed notebooks as the source of operational knowledge; outputs may exist, but code cells should remain understandable without relying on prior execution state.

### Architecture Patterns
- The repository is currently notebook-first, not an application or package.
- Stripe ingestion reads raw Parquet files from Azure Data Lake Storage and materializes them into Databricks tables in `stripe.stripe_data`.
- Current Stripe table workflows target `livemode` data and 2025-prefixed export paths.
- GA4 exploration is local and file-based: CSV exports are loaded into pandas, copied into a local SQLite table, and queried with SQL for fast iteration.
- Reffy owns ideation artifacts and runtime context under `.reffy/`; ReffySpec owns canonical planning/spec files under `.reffy/reffyspec/`.
- Keep `.reffy/reffyspec/specs/` as current capability truth and `.reffy/reffyspec/changes/` as proposed deltas when formal planning is needed.

### Testing Strategy
- There is no automated test suite or CI configuration in this repository yet.
- Validate Databricks notebook changes by running the affected notebook cells against the intended Databricks workspace/cluster and confirming schemas, row counts, and sample queries.
- Validate local GA4 analysis changes by rerunning the notebook against the relevant CSV extract and confirming expected SQLite table creation/query results.
- For Reffy/ReffySpec metadata or artifact changes, run the relevant Reffy validation commands when available, such as `reffy validate` or `reffy plan validate`.
- For data workflows, prefer adding lightweight sanity checks in notebooks: schema inspection, row counts, distinct key/event checks, and limited sample reads.

### Git Workflow
- The repository currently uses `main` as the active branch and `origin` points to `git@github.com:RoskiDeluge/keywrds-data.git`.
- Existing commit history uses concise, descriptive messages such as `Materialized Stripe Customers table from raw data dump`.
- Keep commits scoped by dataset or notebook workflow.
- Do not commit local virtual environments, transient CSV/JSON exports, local SQLite databases, logs, or notebook checkpoints.
- Preserve user-created notebook/data changes in the working tree; inspect before editing because notebooks and sample files may be exploratory.

## Domain Context
- Keywrds.ai data currently represented here includes Stripe billing entities and GA4 web/product analytics events.
- Stripe source data is stored as Parquet in Azure Data Lake Storage and organized by year/date-like prefixes, mode (`livemode`), and entity type (`customers`, `subscriptions`).
- Databricks target schema: `stripe.stripe_data`.
- Current materialized Stripe tables:
  - `stripe.stripe_data.tbl__stripe__initial_raw_customers_data`
  - `stripe.stripe_data.tbl__stripe__initial_raw_subscriptions_data`
- GA4 event exports include nested JSON-like fields such as `event_params`, `device`, `geo`, `traffic_source`, `ecommerce`, `items`, and `session_traffic_source_last_click`.
- Observed GA4 events include `page_view`, `user_engagement`, `session_start`, `first_visit`, `form_start`, `form_submit`, `scroll`, and `signed_up`.

## Important Constraints
- Treat Stripe and GA4 data as sensitive business/customer analytics data. Avoid exposing raw records, credentials, tokens, or personally identifiable data in commits, logs, examples, or specs.
- External data access depends on Databricks workspace credentials and Azure Data Lake permissions; local execution will not reproduce Databricks-only notebook cells.
- Raw data files can be large and should generally remain outside Git. The repository should keep code, notebooks, and planning context rather than durable data dumps.
- Notebook outputs can contain data samples. Review outputs before committing changes that touched sensitive datasets.
- Reffy/ReffySpec managed instruction blocks in `AGENTS.md` should be preserved so `reffy init` can refresh them.

## External Dependencies
- Databricks for notebook execution, Spark/PySpark, Spark SQL, and table materialization.
- Azure Data Lake Storage Gen2 via `abfss://keywrds-stripe-data@keywrdsstripedata.dfs.core.windows.net`.
- Stripe export data for customers and subscriptions.
- GA4 event export data for Keywrds.ai analytics.
- Python notebook environment with pandas for local CSV exploration.
- SQLite for local ad hoc query workflows.
- Reffy/ReffySpec CLI and repository-local metadata under `.reffy/`.
