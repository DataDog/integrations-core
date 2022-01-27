# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.ibm_mq.config import IBMMQConfig

from .common import HOST

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'override_hostname, expected_hostname, expected_tag',
    [(False, None, 'mq_host:{}'.format(HOST)), (True, HOST, None)],
)
def test_mq_tag(instance, override_hostname, expected_hostname, expected_tag):
    instance['override_hostname'] = override_hostname
    config = IBMMQConfig(instance)

    assert config.hostname == expected_hostname
    if expected_tag:
        assert expected_tag in config.tags
