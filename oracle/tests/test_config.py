# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.oracle import Oracle

from .common import CHECK_NAME


def test__get_config(check, instance):
    """
    Test the _get_config method
    """
    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._user == 'system'
    assert check._password == 'oracle'
    assert check._service == 'xe'
    assert check._jdbc_driver is None
    assert check._tags == ['optional:tag1']
    assert check._service_check_tags == ['server:{}'.format(instance['server']), 'optional:tag1']
    assert len(check._query_manager.queries) == 3


def test_check_misconfig(instance):
    """
    Test bad config values
    """
    instance['server'] = None
    check = Oracle(CHECK_NAME, {}, [instance])
    with pytest.raises(ConfigurationError):
        check.validate_config()
