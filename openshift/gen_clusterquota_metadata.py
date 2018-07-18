# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# This script generates metadata for the openshift.*clusterresource.*
# metric family. This allows us to keep them consistent across updates.
# Usage: ./gen_clusterquota_metadata.py > metadata.csv

RESOURCES = [
    "cpu",
    "memory",
    "pods",
    "services",
    "persistentvolumeclaims",
    "services.nodeports",
    "services.loadbalancers",
]

UNITS_PER_RESOURCE = {
    "cpu": "cpu",
    "memory": "byte",
    "storage": "byte",
}

DESC_PER_RESOURCE = {
    "persistentvolumeclaims": "persistent volume claims",
    "services.nodeports": "service node ports",
    "services.loadbalancers": "service load balancers",
}

DESC_PER_COUNT_TYPE = {
    "used": "Observed {} usage",
    "limit": "Hard limit for {}",
    "remaining": "Remaining available {}"
}

ORIENTATION_PER_COUNT_TYPE = {
    "used": 0,
    "limit": 0,
    "remaining": 1
}


def gen_clusterquota_line(resource, count_type, applied=False):
    metric_name = "openshift."
    if applied:
        metric_name += "appliedclusterquota."
    else:
        metric_name += "clusterquota."
    metric_name += resource + "." + count_type

    description = DESC_PER_COUNT_TYPE[count_type].format(DESC_PER_RESOURCE.get(resource, resource))

    description += " by cluster resource quota"
    if applied:
        description += " and namespace"
    else:
        description += " for all namespaces"

    print("{},gauge,,{},,{},{},openshift".format(
        metric_name,
        UNITS_PER_RESOURCE.get(resource, ""),
        description,
        ORIENTATION_PER_COUNT_TYPE[count_type]
    ))


print("metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name")

for res in RESOURCES:
    gen_clusterquota_line(res, "used", False)
    gen_clusterquota_line(res, "limit", False)
    gen_clusterquota_line(res, "remaining", False)

for res in RESOURCES:
    gen_clusterquota_line(res, "used", True)
    gen_clusterquota_line(res, "limit", True)
    gen_clusterquota_line(res, "remaining", True)
