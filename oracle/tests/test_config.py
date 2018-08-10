# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from datadog_checks.oracle import OracleConfigError


def test__get_config(check, instance):
    """
    Test the _get_config method
    """
    server, user, password, service, jdbc_driver, tags, custom_queries = check._get_config(instance)
    assert user == 'system'
    assert password == 'oracle'
    assert service == 'xe'
    assert jdbc_driver is None
    assert tags == ['optional:tag1']
    assert custom_queries == []
    assert check.server == 'localhost:1521'


def test_check_misconfig(check, instance):
    """
    Test bad config values
    """
    instance['server'] = None
    with pytest.raises(OracleConfigError):
        check.check(instance)
