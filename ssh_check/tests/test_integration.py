# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest

from datadog_checks.ssh_check import CheckSSH
from tests.conftest import PRIVATE_KEY_FILE

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, instance):
    check = CheckSSH('ssh_check', {}, [instance])
    check.check(instance)
    common._test_check(aggregator, instance)
    common.wait_for_threads()


@pytest.mark.skipif(common.SSH_SERVER_VERSION is None, reason='No version')
@pytest.mark.usefixtures("dd_environment")
def test_metadata(aggregator, instance, datadog_agent):
    check = CheckSSH('ssh_check', {}, [instance])
    check.check_id = 'test:123'
    check.check(instance)

    _, _, flavor, raw_version = re.split(r'[-_]', common.SSH_SERVER_VERSION)
    major, minor = raw_version.split(".")

    version_metadata = {
        'version.scheme': 'ssh_check',
        'version.major': major,
        'version.minor': minor,
        'version.raw': common.SSH_SERVER_VERSION,
        'flavor': flavor,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)

    common.wait_for_threads()  # needed, otherwise the next won't count correctly threads


@pytest.mark.usefixtures("dd_environment_keypair")
def test_check_keypair(aggregator, instance):
    instance['private_key_file'] = PRIVATE_KEY_FILE
    instance['password'] = 'testpassprase'
    check = CheckSSH('ssh_check', {}, [instance])
    check.check(instance)
    common._test_check(aggregator, instance)
    common.wait_for_threads()
