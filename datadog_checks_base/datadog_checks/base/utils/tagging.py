# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

try:
    import tagger
except ImportError:
    from ..stubs import tagger  # noqa: F401


RESERVED_TAGS = {
    'cluster',
    'device',
    'env',
    'host',
    'service',
    'source',
    'version',
}

GENERIC_TAGS = {
    'cluster_name',
    'clustername',
    'clusterid',
    'cluster_id',
    'host_name',
    'hostname',
    'node',
    'port',
    'server',
}

TAGS_TO_RENAME = RESERVED_TAGS | GENERIC_TAGS
