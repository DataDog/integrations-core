# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mongo import MongoDb

METRICS = [
    'mongodb.connections.available',
    'mongodb.metrics.cursor.open.pinned',
    'mongodb.stats.filesize',
    'mongodb.stats.indexsize',
    'mongodb.connections.totalcreated',
    'mongodb.uptime',
    'mongodb.mem.bits',
    'mongodb.stats.datasize',
    'mongodb.stats.numextents',
    'mongodb.stats.indexes',
    'mongodb.mem.resident',
    'mongodb.metrics.cursor.open.total',
    'mongodb.stats.avgobjsize',
    'mongodb.stats.storagesize',
    'mongodb.mem.virtual',
    'mongodb.dbs',
    'mongodb.fsynclocked',
    'mongodb.stats.objects',
    'mongodb.connections.current',
    'mongodb.network.bytesinps',
    'mongodb.asserts.msgps',
    'mongodb.opcounters.queryps',
    'mongodb.opcounters.getmoreps',
    'mongodb.asserts.rolloversps',
    'mongodb.opcounters.deleteps',
    'mongodb.asserts.regularps',
    'mongodb.opcounters.insertps',
    'mongodb.asserts.warningps',
    'mongodb.metrics.getlasterror.wtime.numps',
    'mongodb.network.numrequestsps',
    'mongodb.opcounters.updateps',
    'mongodb.asserts.userps',
    'mongodb.opcounters.commandps',
    'mongodb.extra_info.page_faultsps',
    'mongodb.network.bytesoutps',
    'mongodb.metrics.getlasterror.wtime.totalmillisps',
]


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance_authdb):
    aggregator = dd_agent_check(instance_authdb, rate=True)
    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK)
