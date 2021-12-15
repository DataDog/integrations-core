# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def rds_parse_tags_from_endpoint(endpoint):
    """
    Given the URI for an AWS RDS / Aurora endpoint, parse supplemental tags
    from the parts. The possible tags are:

    * `dbinstanceidentifier` - The instance's unique identifier for RDS and Aurora clusters
    * `dbclusteridentifier` - The cluster identifier in the case of Aurora cluster endpoints and serverless
    * `hostname` - The full endpoint if the endpoint points to a specific instance. This tag should match
        the RDS integration tag of the same name.
    * `host` - Same value as the hostname tag, but intended to supplement the agent `host` tag since RDS
        instance checks are always run on different hosts from where the actual managed DB is run.
    * `region` - The AWS region of the endpoint

    Examples:

    >>> rds_parse_tags_from_endpoint('customers-04.cfxdfe8cpixl.us-west-2.rds.amazonaws.com')
    ['dbinstanceidentifier:customers-04', 'hostname:customers-04.cfxdfe8cpixl.us-west-2.rds.amazonaws.com',
     'host:customers-04.cfxdfe8cpixl.us-west-2.rds.amazonaws.com', 'region:us-west-2']

    >>> rds_parse_tags_from_endpoint('dd-metrics.cluster-ro-cfxdfe8cpixl.ap-east-1.rds.amazonaws.com')
    ['dbclusteridentifier:dd-metrics', 'region:ap-east-1']
    """
    tags = []

    if not endpoint:
        return tags

    endpoint = endpoint.strip()
    parts = endpoint.split('.', 3)
    if len(parts) != 4:
        return tags
    if parts[3] != 'rds.amazonaws.com':
        return tags

    identifier, cluster, region, _ = parts
    if cluster.startswith('cluster-'):
        tags.append('dbclusteridentifier:' + identifier)
    else:
        tags.append('dbinstanceidentifier:' + identifier)
        tags.append('hostname:' + endpoint)
        tags.append('host:' + endpoint)
    tags.append('region:' + region)
    return tags
