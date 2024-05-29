#!/bin/bash
#
# create-vm <type>
#

VM_TYPE=${1:-default}

DIR_OF_SCRIPT="$(dirname "$(realpath "$0")")"
TEMP_DIR=$(mktemp -d)

source "$DIR_OF_SCRIPT/agent-integrations-openstack" $VM_TYPE

cp -a "$DIR_OF_SCRIPT/terraform/." "$TEMP_DIR"
cd "$TEMP_DIR"

terraform init
terraform apply -auto-approve -input=false

rm -rf $TEMP_DIR