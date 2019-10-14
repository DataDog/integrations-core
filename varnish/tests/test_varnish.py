# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest

from . import common

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]

TAGS = ['cluster:webs', 'varnish_name:default']


def test_check(aggregator, check, instance):
    check.check(instance)
    missing_metrics = []
    for mname in common.COMMON_METRICS:
        try:
            aggregator.assert_metric(mname, count=1, tags=TAGS)
        except AssertionError:
            missing_metrics.append(mname)
    _retry_missing_metrics(aggregator, check, instance, missing_metrics)


def test_inclusion_filter(aggregator, check, instance):
    instance['metrics_filter'] = ['SMA.*']

    check.check(instance)
    missing_included_metrics = []
    excluded_metrics = []

    for mname in common.COMMON_METRICS:
        if 'SMA.' in mname:
            try:
                aggregator.assert_metric(mname, count=1, tags=TAGS)
            except AssertionError:
                missing_included_metrics.append(mname)
        else:
            excluded_metrics.append(mname)

    _retry_missing_metrics(aggregator, check, instance, missing_included_metrics)
    for mname in excluded_metrics:  # Only check for excluded metrics once all metrics have been generated
        aggregator.assert_metric(mname, count=0)


def test_exclusion_filter(aggregator, check, instance):
    instance['metrics_filter'] = ['^SMA.Transient.c_req']
    missing_included_metrics = []
    excluded_metrics = []

    check.check(instance)
    for mname in common.COMMON_METRICS:
        if 'SMA.Transient.c_req' in mname:
            excluded_metrics.append(mname)
        elif 'varnish.uptime' not in mname:
            try:
                aggregator.assert_metric(mname, count=1, tags=TAGS)
            except AssertionError:
                missing_included_metrics.append(mname)

    _retry_missing_metrics(aggregator, check, instance, missing_included_metrics)
    for mname in excluded_metrics:  # Only check for excluded metrics once all metrics have been generated
        aggregator.assert_metric(mname, count=0)


def _retry_missing_metrics(aggregator, check, instance, missing_metrics):
    # Not all metrics are always generated at once
    if missing_metrics:
        time.sleep(2)
        check.check(instance)
        for mname in missing_metrics:
            aggregator.assert_metric(mname, count=1, tags=TAGS)
