#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

SOURCE_REPO_REF=$(git rev-parse HEAD)
if [[ ! "$SOURCE_REPO_REF" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Expected a full tagged commit SHA, got: $SOURCE_REPO_REF" >&2
    exit 1
fi
SOURCE_REPO_BRANCH="${CI_COMMIT_BRANCH:?CI_COMMIT_BRANCH must be set}"

# The receiver workflow always runs from master so release tooling stays current;
# source-repo-branch selects stable vs pre-release behavior and is verified to
# contain source-repo-ref.
payload=$(printf '{"ref":"master","inputs":{"source-repo-ref":"%s","source-repo-branch":"%s"}}' \
    "$SOURCE_REPO_REF" "$SOURCE_REPO_BRANCH")

echo "Dispatching autonomous wheel publishing for integrations-core@$SOURCE_REPO_REF ($SOURCE_REPO_BRANCH)"
set +x
DISPATCH_TOKEN=$(dd-octo-sts token \
    --scope DataDog/integrations-core \
    --policy self.gitlab.release.dispatch-wheel-publishing)
trap 'set +x; dd-octo-sts revoke -t "$DISPATCH_TOKEN" 2>/dev/null || true' EXIT

# A lost success response can produce a duplicate dispatch. That is safe: each
# run uses the same source SHA, the receiver serializes runs per SHA, and
# downstream TUF writes are retry-safe.
curl --fail-with-body --silent --show-error \
    --retry 3 --retry-all-errors --retry-delay 2 --max-time 30 \
    --request POST \
    --header "Accept: application/vnd.github+json" \
    --header "Authorization: Bearer $DISPATCH_TOKEN" \
    --header "X-GitHub-Api-Version: 2022-11-28" \
    --data "$payload" \
    https://api.github.com/repos/DataDog/integrations-core/actions/workflows/release-trigger.yml/dispatches
