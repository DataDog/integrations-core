# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.eks_fargate import EksFargateCheck


def test_check(aggregator, instance):
    check = EksFargateCheck('eks_fargate', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
