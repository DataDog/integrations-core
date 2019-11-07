# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.gunicorn import GUnicornCheck

from .common import CHECK_NAME, GUNICORN_VERSION, INSTANCE


@pytest.mark.skipif(not GUNICORN_VERSION, reason='Require GUNICORN_VERSION')
def test_collect_metadata(aggregator, datadog_agent, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn_bin_path'] = setup_gunicorn['gunicorn_bin_path']

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check_id = 'test:123'
    check.check(instance)

    major, minor, patch = GUNICORN_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': GUNICORN_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


def test_collect_metadata_count(aggregator, datadog_agent, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn_bin_path'] = setup_gunicorn['gunicorn_bin_path']

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check_id = 'test:123'
    check.check(instance)

    datadog_agent.assert_metadata_count(5)


def test_collect_metadata_invalid_binary(aggregator, datadog_agent, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn_bin_path'] = '/bin/not_exist'

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check_id = 'test:123'
    check.check(instance)

    datadog_agent.assert_metadata_count(0)
