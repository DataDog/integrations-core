# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.gunicorn import GUnicornCheck

from .common import CHECK_NAME, CONTAINER_NAME, GUNICORN_VERSION, INSTANCE

# TODO: Test metadata in e2e when we can collect metadata from the agent

CHECK_ID = 'test:123'


def _assert_metadata(datadog_agent):
    major, minor, patch = GUNICORN_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': GUNICORN_VERSION,
    }
    datadog_agent.assert_metadata(CHECK_ID, version_metadata)

    datadog_agent.assert_metadata_count(5)


@pytest.mark.skipif(not GUNICORN_VERSION, reason='Require GUNICORN_VERSION')
def test_collect_metadata_instance(aggregator, datadog_agent, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn'] = setup_gunicorn['gunicorn_bin_path']

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check_id = CHECK_ID
    check.check(instance)

    _assert_metadata(datadog_agent)


@pytest.mark.skipif(not GUNICORN_VERSION, reason='Require GUNICORN_VERSION')
def test_collect_metadata_init_config(aggregator, datadog_agent, setup_gunicorn):
    init_config = {'gunicorn': setup_gunicorn['gunicorn_bin_path']}

    check = GUnicornCheck(CHECK_NAME, init_config, [INSTANCE])
    check.check_id = CHECK_ID
    check.check(INSTANCE)

    _assert_metadata(datadog_agent)


@pytest.mark.skipif(not GUNICORN_VERSION, reason='Require GUNICORN_VERSION')
@pytest.mark.usefixtures('dd_environment')
def test_collect_metadata_docker(aggregator, datadog_agent, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn'] = 'docker exec {} gunicorn'.format(CONTAINER_NAME)

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check_id = CHECK_ID
    check.check(instance)

    _assert_metadata(datadog_agent)


def test_collect_metadata_count(aggregator, datadog_agent, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn'] = setup_gunicorn['gunicorn_bin_path']

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check_id = 'test:123'
    check.check(instance)

    datadog_agent.assert_metadata_count(5)


def test_collect_metadata_invalid_binary(aggregator, datadog_agent, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn'] = '/bin/not_exist'

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check_id = CHECK_ID
    check.check(instance)

    datadog_agent.assert_metadata_count(0)
