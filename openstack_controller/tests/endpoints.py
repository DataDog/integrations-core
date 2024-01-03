# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

NOVA_ENDPOINTS = [
    '^/compute/v2\\.1/limits',
    '^/compute/v2\\.1/os-services',
    '^/compute/v2\\.1/flavors/detail',
    '^/compute/v2\\.1/os-hypervisors/detail',
    '^/compute/v2\\.1/os-quota-sets/[^/]+',
    '^/compute/v2\\.1/servers/detail/project_id=[^/]+',
    '^/compute/v2\\.1/servers/[^/]+/diagnostics',
]

IRONIC_ENDPOINTS = [
    '^/baremetal/v1/nodes/detail',
    '^/baremetal/v1/nodes/detail=True',
    '^/baremetal/v1/conductors',
]
