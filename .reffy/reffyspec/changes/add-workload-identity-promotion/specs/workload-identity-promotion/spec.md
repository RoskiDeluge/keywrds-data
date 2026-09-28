## ADDED Requirements

### Requirement: Secretless production authentication
The deployment workflow SHALL authenticate as `keywrds-data-prod-publisher` through GitHub OIDC without storing a Databricks or Microsoft Entra client secret.

#### Scenario: Authorized production workflow authenticates
- **WHEN** a workflow in `RoskiDeluge/keywrds-data` runs through the GitHub `production` environment
- **THEN** Databricks exchanges its GitHub OIDC token for a Databricks OAuth token
- **AND** audit events identify the publisher service principal

#### Scenario: Untrusted workflow is rejected
- **WHEN** an OIDC token has a repository or environment subject outside the configured trust boundary
- **THEN** Databricks rejects workload authentication

### Requirement: Environment-specific bundle targets
The repository SHALL define development and production bundle targets with explicit workspace, catalog, and schema values.

#### Scenario: Developer validates the development target
- **WHEN** the development bundle target is selected
- **THEN** it resolves to `dbw_sql_dev_westus2` and the development workspace

#### Scenario: CI deploys the production target
- **WHEN** the production workflow deploys the production bundle target
- **THEN** it resolves to `keywrds_data.production` in the production workspace

### Requirement: Least-privilege production publication
The publisher SHALL have read-only access to approved source schemas and table-publication access only within `keywrds_data.production`.

#### Scenario: Publisher materializes an approved model
- **WHEN** approved model code reads a governed source and writes a production table
- **THEN** source data can be selected
- **AND** the output can be created or modified under `keywrds_data.production`

#### Scenario: Publisher attempts broader mutation
- **WHEN** the publisher attempts to modify another catalog or schema
- **THEN** Unity Catalog denies the operation

### Requirement: Explicit production promotion
Production deployment SHALL require an explicit workflow dispatch through the GitHub `production` environment.

#### Scenario: Main branch changes without promotion
- **WHEN** code is merged to `main` without manually dispatching the production workflow
- **THEN** no production bundle deployment occurs
