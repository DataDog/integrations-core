# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = 8765


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


URL = 'http://{}:{}'.format(HOST, PORT)
INSTANCE = {'openmetrics_endpoint': '{}/metrics'.format(URL)}

METRICS = [
    'falco.evt.hostname',
    'falco.container.memory.used',
    'falco.cpu.usage.ratio',
    'falco.duration.seconds.count',
    'falco.evt.source',
    'falco.host.cpu.usage.ratio',
    'falco.host.memory.used',
    'falco.host.num.cpus',
    'falco.host.open.fds',
    'falco.host.procs.running',
    'falco.jemalloc.active.count',
    'falco.jemalloc.allocated.count',
    'falco.jemalloc.mapped.count',
    'falco.jemalloc.metadata.count',
    'falco.jemalloc.metadata.thp.count',
    'falco.jemalloc.resident.count',
    'falco.jemalloc.retained.count',
    'falco.jemalloc.zero.reallocs.count',
    'falco.kernel.release',
    'falco.memory.pss',
    'falco.memory.rss',
    'falco.memory.vsz',
    'falco.outputs.queue.num.drops.count',
    'falco.rules.matches.count',
    'falco.sha256.config.files',
    'falco.sha256.rules.files',
    'falco.scap.engine.name',
    'falco.scap.n.added.fds.count',
    'falco.scap.n.added.threads.count',
    'falco.scap.n.cached.fd.lookups.count',
    'falco.scap.n.cached.thread.lookups.count',
    'falco.scap.n.containers',
    'falco.scap.n.drops.buffer.count',
    'falco.scap.n.drops.full.threadtable.count',
    'falco.scap.n.drops.scratch.map.count',
    'falco.scap.n.drops.count',
    'falco.scap.n.evts.count',
    'falco.scap.n.failed.fd.lookups.count',
    'falco.scap.n.failed.thread.lookups.count',
    'falco.scap.n.fds',
    'falco.scap.n.missing.container.images',
    'falco.scap.n.noncached.fd.lookups.count',
    'falco.scap.n.noncached.thread.lookups.count',
    'falco.scap.n.removed.fds.count',
    'falco.scap.n.removed.threads.count',
    'falco.scap.n.retrieve.evts.drops.count',
    'falco.scap.n.retrieved.evts.count',
    'falco.scap.n.store.evts.drops.count',
    'falco.scap.n.stored.evts.count',
    'falco.scap.n.threads',
]
