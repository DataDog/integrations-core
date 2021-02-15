# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from time import sleep

import pytest

from .common import PROCESSES, PROCESSES_BY_STATE_BY_ITERATION, STATUSES, SUPERVISOR_VERSION

# Mark all tests in this file as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_supervisord(aggregator, check, instance):
    """
    Run Supervisord check and assess coverage
    """
    instance_tags = ["supervisord_server:travis"]

    for i in range(4):
        # Run the check
        check.check(instance)

        # Check metrics and service checks scoped by process
        for proc in PROCESSES:
            process_tags = instance_tags + ["supervisord_process:{}".format(proc)]
            process_status = check.OK if proc in PROCESSES_BY_STATE_BY_ITERATION[i]['up'] else check.CRITICAL

            aggregator.assert_metric("supervisord.process.uptime", tags=process_tags, count=1)
            aggregator.assert_service_check(
                "supervisord.process.status", status=process_status, tags=process_tags, count=1
            )

        # Check instance metrics
        for status in STATUSES:
            status_tags = instance_tags + ["status:{}".format(status)]
            count_processes = len(PROCESSES_BY_STATE_BY_ITERATION[i][status])
            aggregator.assert_metric("supervisord.process.count", value=count_processes, tags=status_tags, count=1)

        aggregator.assert_service_check("supervisord.can_connect", status=check.OK, tags=instance_tags, count=1)
        aggregator.reset()

        # Sleep 10s to give enough time to processes to terminate
        sleep(10)


def test_connection_failure(aggregator, check, bad_instance):
    """
    Service check reports connection failure
    """
    instance_tags = ["supervisord_server:travis"]
    with pytest.raises(Exception):
        check.check(bad_instance)
        aggregator.assert_service_check("supervisord.can_connect", status=check.CRITICAL, tags=instance_tags, count=1)


def test_supervisord_version_metadata(aggregator, check, instance, datadog_agent):
    check.check_id = 'test:123'
    check.check(instance)

    raw_version = SUPERVISOR_VERSION.replace('_', '.')
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'supervisord',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
