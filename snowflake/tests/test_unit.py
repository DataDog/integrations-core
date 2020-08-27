# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import mock
import pytest

from datadog_checks.snowflake import SnowflakeCheck

from .conftest import CHECK_NAME


def test_config():
    # Test missing account
    user_config = {
        'username': 'TestGuy',
        'password': 'badpass',
    }
    with pytest.raises(Exception, match='Must specify an account'):
        SnowflakeCheck(CHECK_NAME, {}, [user_config])

    # Test missing user and pass
    account_config = {'account': 'TEST123'}
    with pytest.raises(Exception, match='Must specify a user and password'):
        SnowflakeCheck(CHECK_NAME, {}, [account_config])


def test_default_metric_groups(instance):
    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    assert check.config.metric_groups == [
        'snowflake.query',
        'snowflake.billing',
        'snowflake.storage',
        'snowflake.logins',
    ]

def test_metric_group_exceptions(instance):
    instance = copy.deepcopy(instance)
    instance['metric_groups'] = ['fake.metric.group']
    with pytest.raises(Exception, match='No valid metric_groups configured, please list at least one.'):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check.log = mock.MagicMock()
        check.log.warning.assert_called_once_with("Invalid metric_groups found in snowflake conf.yaml: fake.metric.group")




