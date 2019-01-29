# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from . import common, metrics


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check):
    check.check(common.INSTANCE)

    server_tag = 'server:{}'.format(common.TOKUMX_SERVER)

    for mname in metrics.GAUGES:
        aggregator.assert_metric(mname, count=1, tags=[server_tag, "optional:tag1"])
    for mname in metrics.RATES:
        aggregator.assert_metric(mname, count=1)
    for msuff in metrics.IDX_HISTS:
        aggregator.assert_metric('tokumx.stats.idx.{}'.format(msuff), at_least=1)
    for msuff in metrics.COLL_HISTS:
        aggregator.assert_metric('tokumx.stats.coll.{}'.format(msuff), at_least=1)
    for msuff in metrics.DB_STATS:
        for dbname in ('admin', 'local', 'test'):
            aggregator.assert_metric(
                'tokumx.stats.db.{}'.format(msuff),
                count=1,
                tags=[server_tag, 'db:{}'.format(dbname), "optional:tag1"]
            )

    sc_tags = [
        'db:admin',
        'host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
        'optional:tag1'
    ]

    aggregator.assert_service_check('tokumx.can_connect', count=1, status=check.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()
