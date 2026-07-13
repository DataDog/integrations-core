# Release Tag STS Credential Design

## Purpose

Allow the reusable wheel-release workflow to create protected integration tags without granting the generic GitHub Actions token a broad repository-rules bypass.

## Architecture

The `prepare` job in `.github/workflows/release-dispatch.yml` will mint a short-lived DD Octo STS GitHub App token before checking out the source repository. The token will use the source repository as its scope and the policy name `self.release.tag-push`. The source checkout will persist that token in Git's local credential configuration, allowing the existing `ddev release tag --push` command to authenticate without handling credentials in shell code.

The workflow-tooling checkout will continue to use the default read-only `GITHUB_TOKEN`. The downstream dispatch job will continue to mint its separate token for `DataDog/agent-integration-wheels-release`; that token has a different repository and purpose.

## Permissions and policy

The default workflow permission will be reduced from `contents: write` to `contents: read`, while retaining `id-token: write` for the OIDC exchange.

The out-of-band `self.release.tag-push` policy must:

- be provisioned for each supported source repository scope;
- trust only the approved release workflow and release environment;
- permit only the repository write operations needed to create release tags; and
- restrict use to intended stable and prerelease refs.

The organization tag ruleset must list the DD Octo STS integration, ID 1157446, as an always-bypass actor. The STS policy remains the least-privilege control over which workflow may exercise that app identity.

## Data flow

1. The caller grants `contents: read` and `id-token: write` to the reusable workflow.
2. The `prepare` job checks out workflow tooling with the default token.
3. DD Octo STS exchanges the job's OIDC identity for a short-lived source-repository token.
4. The source checkout receives and persists that token.
5. `release_prepare.py` invokes `ddev release tag --push`.
6. Git uses the persisted App token; GitHub evaluates the DD Octo STS actor against the tag ruleset.
7. The existing dispatch job separately mints a destination-repository token for wheel-build dispatch.

## Failure handling

Token issuance or source checkout failure stops the job before any tag is created. A ruleset or policy misconfiguration remains visible as an STS, checkout, or push failure. Existing ddev behavior remains unchanged: it fetches tags before creating one and treats an already-existing tag as an idempotent no-op.

## Testing

Add workflow-structure tests that parse the release workflow and verify:

- the source-tag token step precedes source checkout;
- the token uses the dynamic source repository scope and `self.release.tag-push` policy;
- source checkout receives the token and persists credentials;
- default contents permissions are read-only; and
- the downstream dispatch token remains scoped to the wheel-release repository.

Run the focused workflow tests, repository workflow validation, formatting, and lint checks through `ddev`.

## Rollout

Provision the STS policy and ruleset bypass before merging or enabling the workflow change. After rollout, recover the lustre release by manually dispatching the fixed workflow from `master` with source SHA `02a88148c268bf6c620289434f2abec62ac06412`, branch `beta/lustre-issue-24475`, and package `lustre`.
