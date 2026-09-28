## 1. Planning
- [x] 1.1 Review the selected Reffy artifacts and confirm the native Databricks scope.
- [x] 1.2 Define the OIDC trust boundary, environment model, and least-privilege grants.
- [x] 1.3 Validate the refined ReffySpec change.

## 2. Identity and access
- [x] 2.1 Create a Databricks federation policy for the GitHub `production` environment.
- [x] 2.2 Grant the publisher read access to governed production source schemas.
- [x] 2.3 Verify destination publication and source read permissions.

## 3. Repository automation
- [x] 3.1 Add the multi-target Databricks bundle configuration.
- [x] 3.2 Add the secretless GitHub Actions production deployment workflow.
- [x] 3.3 Document environment boundaries and promotion behavior.
- [x] 3.4 Configure the GitHub `production` environment variables and deployment policy.

## 4. Verification
- [x] 4.1 Validate both bundle targets with `--strict`.
- [x] 4.2 Validate the completed ReffySpec change.
- [x] 4.3 Review the final diff for credentials or sensitive data.
