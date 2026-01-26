#!/bin/bash

set -ex

# Only required on non-master branches
# To benefit from ci visibility, ddtrace needs to explore git and the local clone we do in ddev tests
# from a shallow repo can break it. Lets get the full repo so we have a proper repo to clone from locally.

if [ "$(git rev-parse --is-shallow-repository)" = "true" ]; then
  echo "Repository is shallow. Unshallowing to get full history..."
  # --unshallow: Downloads the rest of the commit history
  # --tags: Ensures we get tags (useful for versioning)
  # -f: Force update references if needed
  git fetch --unshallow --tags -f origin
fi

# 2. Your original logic: Ensure we have the master branch reference locally
# (Unshallowing gets the history, but doesn't necessarily create the local 'master' ref)
if [[ "$GITHUB_REF_NAME" != "master" ]]; then
  git fetch origin master:master
fi

set +ex
