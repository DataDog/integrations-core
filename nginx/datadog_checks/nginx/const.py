# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

PLUS_API_ENDPOINTS = {
    "nginx": [],
    "http/requests": ["requests"],
    "http/server_zones": ["server_zones"],
    "http/upstreams": ["upstreams"],
    "http/caches": ["caches"],
    "processes": ["processes"],
    "connections": ["connections"],
    "ssl": ["ssl"],
    "slabs": ["slabs"],
}

PLUS_API_STREAM_ENDPOINTS = {
    "stream/server_zones": ["stream", "server_zones"],
    "stream/upstreams": ["stream", "upstreams"],
}

PLUS_API_V3_STREAM_ENDPOINTS = {
    "stream/zone_sync": ["stream", "zone_sync"],
}

TAGGED_KEYS = {
    'caches': 'cache',
    'server_zones': 'server_zone',
    'serverZones': 'server_zone',  # VTS
    'upstreams': 'upstream',
    'upstreamZones': 'upstream',  # VTS
    'slabs': 'slab',
    'slots': 'slot',
    'zones': 'zone',
}
