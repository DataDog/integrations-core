#!/bin/bash

if [ "$GITHUB_EVENT_NAME" == "pull_request" ]; then
  prev_sha=$PR_BASE_SHA
  curr_sha=$PR_HEAD_SHA
else
  prev_sha=$EVENT_BEFORE
  curr_sha=$GITHUB_SHA
fi

echo "prev_sha=$prev_sha" >> $GITHUB_OUTPUT
echo "curr_sha=$curr_sha" >> $GITHUB_OUTPUT

echo "Current SHA: $curr_sha"
echo "Previous SHA: $prev_sha"
