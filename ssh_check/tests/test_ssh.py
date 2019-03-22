# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading

import pytest

from datadog_checks.ssh_check import CheckSSH
from . import common


def test_ssh(aggregator):
    c = CheckSSH('ssh_check', {}, {}, list(common.INSTANCES.values()))

    nb_threads = threading.active_count()

    c.check(common.INSTANCES['main'])

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.OK
        for tag in sc.tags:
            assert tag in ('instance:io.netgarage.org-22', 'optional:tag1')

    # Check that we've closed all connections, if not we're leaking threads
    common.wait_for_threads()
    assert nb_threads == threading.active_count()


def test_ssh_bad_config(aggregator):
    c = CheckSSH('ssh_check', {}, {}, list(common.INSTANCES.values()))

    nb_threads = threading.active_count()

    with pytest.raises(Exception):
        c.check(common.INSTANCES['bad_auth'])

    with pytest.raises(Exception):
        c.check(common.INSTANCES['bad_hostname'])

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.CRITICAL

    # Check that we've closed all connections, if not we're leaking threads
    common.wait_for_threads()
    assert nb_threads == threading.active_count()
