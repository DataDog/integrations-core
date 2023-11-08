#!/bin/bash
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euxo pipefail
IFS=$'\n\t'

curl --request POST --form "token=$CI_JOB_TOKEN" --form ref=master \
  --form variables[ORIG_CI_BUILD_REF]=$CI_COMMIT_SHA \
  --form variables[ROOT_LAYOUT_TYPE]=core \
  --form variables[REPO_NAME]=integrations-core \
  https://gitlab.ddbuild.io/api/v4/projects/138/trigger/pipeline

