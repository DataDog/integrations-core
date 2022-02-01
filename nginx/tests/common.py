# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname
from datadog_checks.nginx.metrics import COUNT_METRICS, METRICS_SEND_AS_COUNT

CHECK_NAME = 'nginx'

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, 'fixtures')

HOST = get_docker_hostname()
PORT = '8080'
PORT_SSL = '8081'
TAGS = ['foo:foo', 'bar:bar']
USING_VTS = os.getenv('NGINX_IMAGE', '').endswith('nginx-vts')
USING_LATEST = os.getenv('NGINX_IMAGE', '').endswith('latest')
NGINX_VERSION = os.getenv('NGINX_VERSION', os.environ.get('NGINX_IMAGE'))

GAUGE_PLUS_METRICS = [
    'nginx.cache.cold',
    'nginx.cache.max_size',
    'nginx.cache.size',
    'nginx.connections.active',
    'nginx.connections.idle',
    'nginx.load_timestamp',
    'nginx.pid',
    'nginx.ppid',
    'nginx.requests.current',
    'nginx.server_zone.processing',
    'nginx.slab.pages.free',
    'nginx.slab.pages.used',
    'nginx.slab.slot.fails',
    'nginx.slab.slot.free',
    'nginx.slab.slot.reqs',
    'nginx.slab.slot.used',
    'nginx.stream.server_zone.processing',
    'nginx.stream.upstream.peers.active',
    'nginx.stream.upstream.peers.backup',
    'nginx.stream.upstream.peers.connect_time',
    'nginx.stream.upstream.peers.downstart',
    'nginx.stream.upstream.peers.first_byte_time',
    'nginx.stream.upstream.peers.health_checks.last_passed',
    'nginx.stream.upstream.peers.id',
    'nginx.stream.upstream.peers.max_conns',
    'nginx.stream.upstream.peers.response_time',
    'nginx.stream.upstream.peers.selected',
    'nginx.stream.upstream.peers.weight',
    'nginx.stream.upstream.zombies',
    'nginx.stream.zone_sync.status.bytes_in',
    'nginx.stream.zone_sync.status.bytes_out',
    'nginx.stream.zone_sync.status.msgs_in',
    'nginx.stream.zone_sync.status.msgs_out',
    'nginx.stream.zone_sync.status.nodes_online',
    'nginx.stream.zone_sync.zone.records_pending',
    'nginx.timestamp',
    'nginx.upstream.keepalive',
    'nginx.upstream.peers.active',
    'nginx.upstream.peers.backup',
    'nginx.upstream.peers.downstart',
    'nginx.upstream.peers.header_time',
    'nginx.upstream.peers.health_checks.last_passed',
    'nginx.upstream.peers.id',
    'nginx.upstream.peers.max_conns',
    'nginx.upstream.peers.response_time',
    'nginx.upstream.peers.selected',
    'nginx.upstream.peers.weight',
    'nginx.upstream.zombies',
]
METRICS_SEND_AS_COUNT_COUNTS = [metric + "_count" for metric in METRICS_SEND_AS_COUNT]
ALL_PLUS_METRICS = METRICS_SEND_AS_COUNT_COUNTS + METRICS_SEND_AS_COUNT + COUNT_METRICS + GAUGE_PLUS_METRICS
