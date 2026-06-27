---
title: Databricks Egress — Initial Table Scope (v1)
status: exploratory
---

# Databricks Egress — Initial Table Scope (v1)

Concrete table selection for the first `dlt` snapshot from DO Postgres into
Unity Catalog. Companion to
[`databricks_postgres_egress_exploration.md`](.reffy/artifacts/databricks_postgres_egress_exploration.md:1)
(the chosen approach) and
[`dlt_databricks_destination_reference.md`](.reffy/artifacts/dlt_databricks_destination_reference.md:1)
(the destination mechanics).

Table names verified against the running dev database (Docker `db` container,
`keywrds` DB) on 2026-06-25.

## Scope decision

Start with **two tables only** — Customers and Subscriptions. Product
engagement tables (`projects_*`, `chat_*`) are deferred; basic per-customer
engagement is already available via denormalized counters on the customer
table (see below).

```python
table_names=[
    "users_customuser",      # Customers
    "djstripe_subscription", # Subscriptions
]
```

## Why these two

### `users_customuser` (Customers)
Effectively a mini customer-360 in one row:
- **Identity:** `email`, `first_name`, `last_name`, `username`, `date_joined`,
  `is_active`, `last_login`.
- **Billing flags / links:** `paid_account`, `customer_id`,
  `subscription_id`, `last_synced_with_stripe`, `billing_details_last_changed`.
- **Denormalized engagement counters** (free engagement read without the
  `projects_*` tables): `keyword_count`, `outline_count`, `question_count`,
  `answer_count`, `credits`, `tokens`, `free_generation`,
  `free_niche_expander_generation`.

### `djstripe_subscription` (Subscriptions)
The subscription record per customer. **Caveat:** on this dj-stripe version
the table has almost no flat business columns — `status`,
`current_period_end`, plan, and amounts all live inside the **`stripe_data`
JSONB** blob. Relational columns are mostly IDs/timestamps
(`djstripe_id`, `id`, `customer_id`, `created`, `metadata`).

## Join key

These two join directly — no need to pull `djstripe_customer` for v1:

```
users_customuser.subscription_id  →  djstripe_subscription.djstripe_id
users_customuser.customer_id      →  djstripe_customer.djstripe_id   (later)
```

So customer → subscription is a single join.

## Handling notes (carry into the notebook)

1. **Drop the password hash.** `users_customuser` includes `password` (and
   `last_login`). Even with "raw PII is acceptable," there is no reason to
   egress credential hashes. `sql_database` pulls whole tables by default, so
   map the column out:
   ```python
   source = sql_database(CONN, table_names=["users_customuser", "djstripe_subscription"])
   source.users_customuser.add_map(
       lambda row: {k: v for k, v in row.items() if k != "password"}
   )
   ```
2. **`stripe_data` is JSONB.** dlt lands it as a nested/variant column in
   Databricks. Subscription **status** lives there
   (`stripe_data->>'status'`), so plan to flatten it downstream — or add a
   `@dlt.transformer` to lift `status` / `current_period_end` to top-level
   columns at load time.
3. **Plan name not included.** With only `djstripe_subscription`, "which plan"
   is a Stripe price/product ID inside `stripe_data`, not a human name. Add
   `djstripe_product` / `djstripe_price` later if plan names are needed.

## Limitations / next steps

- **Dev data is tiny** (~3 users, ~3 subscriptions) — good for validating
  pipeline mechanics only. Run against **prod (read replica)** for a
  meaningful snapshot.
- Engagement beyond the denormalized counters (per-project / per-keyword /
  GSC opportunity detail, chat activity) is deferred to a later grab via
  `projects_*` and `chat_*`.
- Adding `djstripe_customer`, `djstripe_product`, `djstripe_price` rounds out
  the subscription picture (plan names, customer email reconciliation) when
  needed.

## Reffy References

- `databricks_postgres_egress_exploration.md` — chosen `dlt` one-off-snapshot
  approach and deployment constraints this scope plugs into.
- `dlt_databricks_destination_reference.md` — staging, auth, and Direct Load
  mechanics for the destination side.

## Provenance

Copied from remote Reffy workspace `keywrds-ai`, project `keywrds-ai`, artifact
`.reffy/artifacts/databricks_initial_table_scope.md` on 2026-06-25.
