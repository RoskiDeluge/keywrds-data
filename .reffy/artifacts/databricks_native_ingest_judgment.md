---
title: Databricks-Native Ingest Judgment
status: exploratory
---

# Databricks-Native Ingest Judgment

## Judgment

`dlt` remains worth tracking, but it has not yet justified becoming the
default ingestion layer for this Databricks-centered workflow.

The project benefits from portability and source abstractions in principle, but
this use case is already inside Databricks, targets Unity Catalog, and can be
implemented with fewer moving parts using native Spark, Delta, Unity Catalog,
and Databricks Workflows primitives.

Until `dlt` demonstrates clear operational leverage for this actual workload,
prefer the native Databricks path.

## Why

The core workflow is straightforward:

```text
DigitalOcean Postgres -> Spark JDBC -> Delta/Unity Catalog table
```

That path already worked in the serverless notebook and avoided the failing
`databricks-sql-connector` state-sync path.

For this project, "pipeline semantics" are not a reason by themselves to adopt
`dlt`, because Databricks already provides native pipeline and operational
building blocks:

- Workflows / Jobs for scheduling, retries, and orchestration.
- Spark JDBC for extraction from Postgres.
- Delta tables for durable storage and table history.
- `MERGE INTO` for incremental upserts when needed.
- Unity Catalog for governance.
- Native SQL/Python notebooks or wheels for maintainable job code.
- Lakeflow / Databricks-native declarative pipelines if the workload later
  needs managed transformation semantics.

## Abstraction Boundary Concern

A portable ETL abstraction is attractive in principle, especially for teams
with many sources and destinations. At enterprise scale, that abstraction can
become leaky in the exact areas that matter operationally:

- identity and auth differ per platform,
- networking differs per runtime,
- governance is destination-native,
- observability is platform-native,
- incremental semantics vary by source and destination,
- failure recovery depends on storage, state, and orchestration details,
- performance tuning is usually warehouse/runtime-specific.

So the generic layer has to prove that it removes more complexity than it adds.
In this case, the first real `dlt` attempt introduced extra state-sync and SQL
connector behavior before any data was loaded, while the native Spark path was
simple and successful.

## Decision For Now

Use native Databricks primitives for the first production ingest path:

1. Extract with Spark JDBC from the Postgres read endpoint or read replica.
2. Drop sensitive columns such as password hashes before writing.
3. Write raw tables to Unity Catalog/Delta.
4. Add Databricks Jobs/Workflows scheduling only when repetition is needed.
5. Add incremental `MERGE INTO` logic only when the refresh cadence justifies it.

Reconsider `dlt` later only if one of these becomes true:

- portability outside Databricks becomes a real requirement,
- source abstraction coverage materially reduces maintenance,
- incremental/state handling in `dlt` proves more reliable than native
  Databricks jobs for this workload,
- the upstream Databricks Direct Load/serverless failure mode is fixed or
  clearly documented with a low-friction configuration path.

## Reffy References

- `dlt_serverless_failure_report.md` -- concrete failure mode and successful
  Spark JDBC fallback.
- `databricks_initial_table_scope.md` -- initial table scope for the ingest.
- `databricks_postgres_egress_exploration.md` -- original design that chose
  `dlt` as the first tool to test and identified Spark JDBC as fallback.
- `dlt_databricks_destination_reference.md` -- destination mechanics that show
  the added staging/state/connector surface area.
