#!/bin/bash
#
# source agent-integrations-openstack <type>
#

VM_TYPE=${1:-default}

export TF_VAR_credentials_file="${GCP_SERVICE_ACCOUNT_PATH:-$HOME/service_accounts/agent-integrations-openstack.json}"
export TF_VAR_main_script_path="$(realpath ./tests/e2e-gcp/script.sh)"
export TF_VAR_install_deps_script_path="$(realpath ./tests/e2e-gcp/${VM_TYPE}/install_deps.sh)"
export TF_VAR_local_conf_path="$(realpath ./tests/e2e-gcp/${VM_TYPE}/local.conf)"
export TF_VAR_instance_name="agent-integrations-openstack-${VM_TYPE}"
export TF_VAR_user=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
export TF_VAR_desired_status="RUNNING"
export TF_VAR_nat_ip="$(gcloud compute addresses list --project "datadog-integrations-lab" --filter="name=('${TF_VAR_instance_name}')" --format="get(address)")"
export TF_VAR_network_ip="$(gcloud compute addresses list --project "datadog-integrations-lab" --filter="name=('${TF_VAR_instance_name}-int')" --format="get(address)")"