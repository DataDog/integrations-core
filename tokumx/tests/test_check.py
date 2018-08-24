# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

from datadog_checks.tokumx import TokuMX

from . import common, metrics

log = logging.getLogger(__file__)


def test_check(aggregator, check, spin_up_tokumx):
    check.check(common.INSTANCE)

    server_tag = 'server:%s' % common.MONGO_SERVER

    for k, v in aggregator._metrics.iteritems():
        log.warning("{}: {}".format(k, v))


    for mname in metrics.GAUGES:
        aggregator.assert_metric(mname, count=1, tags=[server_tag, "optional:tag1"])
    for mname in metrics.RATES:
        aggregator.assert_metric(mname, count=1)
    for msuff in metrics.IDX_HISTS:
        for hsuff in metrics.HIST_SUFFIXES:
            aggregator.assert_metric('tokumx.stats.idx.%s.%s' % (msuff, hsuff), count=1)
    for msuff in metrics.IDX_LCL_RATES:
        for hsuff in metrics.HIST_SUFFIXES:
            aggregator.assert_metric('tokumx.statsd.idx.%s.%s' % (msuff, hsuff), count=1)
    for msuff in metrics.COLL_HISTS:
        for hsuff in metrics.HIST_SUFFIXES:
            aggregator.assert_metric('tokumx.stats.coll.%s.%s' % (msuff, hsuff), count=1)
    for msuff in metrics.DB_STATS:
        for dbname in ('admin', 'local', 'test'):
            aggregator.assert_metric('tokumx.stats.db.%s' % (msuff), count=1,
                                     tags=[server_tag, 'db:%s' % dbname, "optional:tag1"])

    sc_tags = [
        'db:test',
        'host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
        'optional:tag1'
    ]
    aggregator.assert_service_check('tokumx.can_connect', count=1, status=TokuMX.OK,
        tags=sc_tags)

    aggregator.assert_all_metrics_covered()
