# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

PCVM_NAME = "NTNX-10-0-0-165-PCVM-1767014640"
UBUNTU_VM_NAME = "ubuntu-vm"
RANDOM_VM_NAME = "random-vm"
OFF_VM_NAME = "test-vm-that-should-remain-off"
HOST_NAME = "10-0-0-103-aws-us-east-1a"

BASE_TAGS = ['nutanix', 'prism_central:10.0.0.197']

CLUSTER_TAGS = [
    'Team:agent-integrations',
    'cluster_category:cluster_value1',
    'cluster_category:cluster_value2',
    'cluster_category:cluster_value3',
    'ntnx_cluster_name:datadog-nutanix-dev',
    'nutanix',
    'prism_central:10.0.0.197',
]

HOST_TAGS = [
    'Team:agent-integrations',
    'cluster_category:cluster_value1',
    'cluster_category:cluster_value2',
    'cluster_category:cluster_value3',
    'ntnx_cluster_name:datadog-nutanix-dev',
    'ntnx_host_name:10-0-0-103-aws-us-east-1a',
    'ntnx_host_type:HYPER_CONVERGED',
    'ntnx_hypervisor_name:AHV 10.3',
    'ntnx_hypervisor_type:AHV',
    'ntnx_type:host',
    'nutanix',
    'prism_central:10.0.0.197',
]

PCVM_TAGS = [
    'ntnx_cluster_name:datadog-nutanix-dev',
    'ntnx_host_name:10-0-0-103-aws-us-east-1a',
    'ntnx_is_agent_vm:False',
    'ntnx_type:vm',
    'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
    'nutanix',
    'prism_central:10.0.0.197',
]

UBUNTU_VM_TAGS = [
    'Team:agent-integrations',
    'ntnx_cluster_name:datadog-nutanix-dev',
    'ntnx_host_name:10-0-0-103-aws-us-east-1a',
    'ntnx_is_agent_vm:False',
    'ntnx_type:vm',
    'ntnx_vm_name:ubuntu-vm',
    'nutanix',
    'prism_central:10.0.0.197',
    'vm_category:vm_value2',
]

RANDOM_VM_TAGS = [
    'Team:agent-integrations',
    'Team:platform-integrations',
    'ntnx_cluster_name:datadog-nutanix-dev',
    'ntnx_host_name:10-0-0-103-aws-us-east-1a',
    'ntnx_is_agent_vm:False',
    'ntnx_type:vm',
    'ntnx_vm_name:random-vm',
    'nutanix',
    'prism_central:10.0.0.197',
    'vm_category:vm_value1',
]

OFF_VM_TAGS = [
    'ntnx_cluster_name:datadog-nutanix-dev',
    # 'ntnx_host_name:None',
    'ntnx_is_agent_vm:False',
    'ntnx_type:vm',
    'ntnx_vm_name:test-vm-that-should-remain-off',
    'nutanix',
    'prism_central:10.0.0.197',
    'vm_category:vm_value3',
]
