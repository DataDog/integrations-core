#!/bin/bash

set -e

WORKFLOW_NAME=$1

# Get merge base commit
echo "Getting merge base commit..."
git fetch origin master:refs/remotes/origin/master
BASE_SHA=$(git merge-base HEAD origin/master)
echo "Base SHA: $base_sha"

# Find workflow run at exact merge-base SHA
echo "Finding workflow run at merge-base SHA..."

if [ -z "$GH_TOKEN" ]; then
    echo "Error: GH_TOKEN environment variable is required"
    exit 1
fi

count=$(git rev-list --count $BASE_SHA..origin/master)
count_plus_one=$((count + 1))

echo "Searching through $count_plus_one workflow runs..."

RUN_ID=$(
    (
        gh run list --workflow $WORKFLOW_NAME --limit $count_plus_one --branch "master" --json databaseId,headSha,event
    ) | jq -s '[.[][]] | .[] | select(.headSha == "'"$BASE_SHA"'") | .databaseId' | head -n 1
)

if [ -z "$RUN_ID" ]; then
    echo "No workflow run found for SHA: $BASE_SHA"
    exit 1
fi

echo "Found workflow run ID: $RUN_ID"

# Output results
echo "run_id=$RUN_ID"
echo "base_sha=$BASE_SHA"
