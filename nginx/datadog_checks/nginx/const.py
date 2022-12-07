# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

PLUS_API_ENDPOINTS = {
    '1': {
        "nginx": [],
        "http/requests": ["requests"],
        "http/server_zones": ["server_zones"],
        "http/upstreams": ["upstreams"],
        "http/caches": ["caches"],
        "processes": ["processes"],
        "connections": ["connections"],
        "ssl": ["ssl"],
        "slabs": ["slabs"],
    },
    '5': {
        "http/location_zones": ["location_zones"],
        "resolvers": ["resolvers"],
    },
    '6': {
        "http/limit_reqs": ["limit_reqs"],
        "http/limit_conns": ["limit_conns"],
    },
}

PLUS_API_STREAM_ENDPOINTS = {
    '1': {
        "stream/server_zones": ["stream", "server_zones"],
        "stream/upstreams": ["stream", "upstreams"],
    },
    '3': {
        "stream/zone_sync": ["stream", "zone_sync"],
    },
    '6': {
        "stream/limit_conns": ["stream", "limit_conns"],
    },
}

TAGGED_KEYS = {
    'caches': 'cache',
    'codes': 'code',
    'limit_conns': 'limit_conn',
    'limit_reqs': 'limit_req',
    'location_zones': 'location_zone',
    'resolvers': 'resolver',
    'server_zones': 'server_zone',
    'serverZones': 'server_zone',  # VTS
    'slabs': 'slab',
    'slots': 'slot',
    'upstreams': 'upstream',
    'upstreamZones': 'upstream',  # VTS
    'zones': 'zone',
}
