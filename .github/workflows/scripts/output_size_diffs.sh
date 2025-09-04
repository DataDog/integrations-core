#!/bin/bash

# Script to join size diffs in order and output PR comments

set -e

# Check required environment variables
if [ -z "$GH_TOKEN" ]; then
    echo "Error: GH_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$GITHUB_RUN_ID" ]; then
    echo "Error: GITHUB_RUN_ID environment variable is required"
    exit 1
fi

if [ -z "$GITHUB_REPOSITORY" ]; then
    echo "Error: GITHUB_REPOSITORY environment variable is required"
    exit 1
fi

if [ -z "$PR_NUMBER" ]; then
    echo "Error: PR_NUMBER environment variable is required"
    exit 1
fi


# Configuration
MAX_COMMENT_SIZE=${MAX_COMMENT_SIZE:-65536}

git fetch origin master:refs/remotes/origin/master
BASE_SHA=$(git merge-base HEAD origin/master)

# Create short base SHA
BASE_SHORT="${BASE_SHA:0:7}"

# Join size diffs in order
echo "<h3>Dependency Size Changes</h3>" > comment.txt
echo >> comment.txt
echo "Comparing with base [($BASE_SHORT)](https://github.com/$GITHUB_REPOSITORY/commit/$BASE_SHA)" >> comment.txt

for p in $PLATFORMS; do
    echo "Downloading size diffs for platform: $p"
    if gh run download "$GITHUB_RUN_ID" --name "size_diffs_output_${p}.txt"; then
        cat "size_diffs_output_${p}.txt" >> comment.txt
    else
        echo "Warning: Could not download size diffs for platform $p"
    fi
done

# Check comment size and use short version if needed
comment_size=$(wc -c < comment.txt)
echo "Comment size: $comment_size bytes (max: $MAX_COMMENT_SIZE)"

if [ $comment_size -gt $MAX_COMMENT_SIZE ]; then
    echo "Comment too large, switching to short version..."
    echo "<h3>Dependency Size Changes</h3>" > comment.txt
    echo >> comment.txt
    echo "Comparing with base [($BASE_SHORT)](https://github.com/$GITHUB_REPOSITORY/commit/$BASE_SHA)" >> comment.txt
    
    for p in $PLATFORMS; do
        echo "Downloading short size diffs for platform: $p"
        if gh run download "$GITHUB_RUN_ID" --name "size_diffs_output_short_${p}.txt"; then
            cat "size_diffs_output_short_${p}.txt" >> comment.txt
        else
            echo "Warning: Could not download short size diffs for platform $p"
        fi
    done
    
    GITHUB_RUN_URL="https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
    echo "<br/><a href=\"$GITHUB_RUN_URL\">📋 View detailed breakdown in GitHub Step Summary</a>" >> comment.txt
fi

# Output results
echo "Posting comment to PR #$PR_NUMBER"
gh pr comment "$PR_NUMBER" --delete-last --yes --repo "$GITHUB_REPOSITORY"
gh pr comment "$PR_NUMBER" --body-file comment.txt --repo "$GITHUB_REPOSITORY"

