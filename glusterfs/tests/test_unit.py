# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from unittest import mock

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.glusterfs import GlusterfsCheck
from datadog_checks.glusterfs.gluster_xml import GlusterXMLError

from .common import CHECK, EXPECTED_METRICS, INIT_CONFIG

pytestmark = pytest.mark.unit

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures', 'gluster')


def _fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def _fake_run_gluster(*args, xml=True):
    if args == ('--version',):
        return _fixture('version.txt')
    fixtures = {
        ('volume', 'info'): 'volume_info.xml',
        ('volume', 'status', 'all', 'detail'): 'volume_status.xml',
        ('pool', 'list'): 'pool_list.xml',
        ('volume', 'heal', 'gv0', 'info'): 'heal_info.xml',
    }
    filename = fixtures.get(tuple(args))
    if filename is None and len(args) == 4 and args[:2] == ('volume', 'heal') and args[3] == 'info':
        filename = 'heal_info.xml'
    if filename is None:
        raise AssertionError(f"Unexpected gluster command in test: {args}")
    return _fixture(filename)


def test_check(aggregator, instance, mock_gluster_xml):
    check = GlusterfsCheck(CHECK, INIT_CONFIG, [instance])
    check.check(instance)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_emits_metrics_when_heal_fails(aggregator, instance):
    # When self-heal info is unavailable (e.g. the self-heal daemon is
    # unresponsive), the check must still emit cluster/volume/brick metrics
    # rather than aborting. Only the heal_info metric should be absent.
    def failing_heal(*args, xml=True):
        if len(args) == 4 and args[0] == 'volume' and args[1] == 'heal' and args[3] == 'info':
            raise GlusterXMLError('self-heal daemon not responding')
        return _fake_run_gluster(*args, xml=xml)

    with mock.patch('datadog_checks.glusterfs.check.GlusterfsCheck._run_gluster', side_effect=failing_heal):
        check = GlusterfsCheck(CHECK, INIT_CONFIG, [instance])
        check.check(instance)

    for metric in EXPECTED_METRICS:
        if metric == 'glusterfs.heal_info.entries.count':
            aggregator.assert_metric(metric, count=0)
        else:
            aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()


def test_parse_version(instance):
    c = GlusterfsCheck(CHECK, INIT_CONFIG, [instance])
    major, minor, patch = c.parse_version('3.13.2')
    assert major == '3'
    assert minor == '13'
    assert patch == '2'
