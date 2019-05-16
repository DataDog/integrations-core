#!/bin/bash
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euxo pipefail
IFS=$'\n\t'

echo "Grabbing secrets"
set +x
export DD_API_KEY=$(aws ssm get-parameter --region us-east-1 --name ci.integrations-core.dd_api_key_trello --with-decryption --query "Parameter.Value" --out text)
export TRELLO_KEY=$(aws ssm get-parameter --region us-east-1 --name ci.integrations-core.trello_release_key --with-decryption --query "Parameter.Value" --out text)
export TRELLO_TOKEN=$(aws ssm get-parameter --region us-east-1 --name ci.integrations-core.trello_release_token --with-decryption --query "Parameter.Value" --out text)
set -x

echo "Running reminder"
python ./.gitlab/reminder/remind.py
