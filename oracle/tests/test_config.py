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
    _, user, password, service, jdbc_driver, tags, only_custom_queries = check._get_config(instance)
    assert user == 'system'
    assert password == 'oracle'
    assert service == 'xe'
    assert jdbc_driver is None
    assert tags == ['optional:tag1']
    assert only_custom_queries is False


def test_check_misconfig(instance):
    """
    Test bad config values
    """
    instance['server'] = None
    check = Oracle(CHECK_NAME, {}, [instance])
    with pytest.raises(ConfigurationError):
        check.validate_config()
