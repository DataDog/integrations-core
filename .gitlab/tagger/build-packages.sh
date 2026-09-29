#!/bin/bash
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euxo pipefail
IFS=$'\n\t'

# --fail-with-body is load-bearing: curl exits 0 on HTTP 4xx/5xx, so without it `set -e`
# cannot catch a rejected trigger and this job reports success having built no wheels.
# The pipeline is addressed by numeric project ID, so a namespace move or a revoked
# job-token scope surfaces only as an HTTP error here.
curl --fail-with-body --request POST --form "token=$CI_JOB_TOKEN" --form ref=master \
  --form variables[ORIG_CI_BUILD_REF]=$CI_COMMIT_SHA \
  --form variables[ROOT_LAYOUT_TYPE]=core \
  --form variables[REPO_NAME]=integrations-core \
  https://gitlab.ddbuild.io/api/v4/projects/13727/trigger/pipeline

