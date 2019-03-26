# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.ssl import SslCheck
from . import common


def test_local_cert(aggregator, instance_local_cert):
    ssl_check = SslCheck(common.CHECK_NAME, {}, {})
    ssl_check.check(instance_local_cert)
    aggregator.assert_all_metrics_covered()


def test_remote_cert(aggregator, instance_remote_cert):
    ssl_check = SslCheck(common.CHECK_NAME, {}, {})
    ssl_check.check(instance_remote_cert)
    aggregator.assert_all_metrics_covered()
