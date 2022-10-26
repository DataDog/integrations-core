# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import tenacity
from mock import mock

from datadog_checks.dev import EnvVars, environment_run
from datadog_checks.dev._env import E2E_SET_UP, E2E_TEAR_DOWN, set_up_env, tear_down_env
from datadog_checks.dev.ci import running_on_ci


def test_set_up_env_default_true():
    with EnvVars(ignore=[E2E_SET_UP]):
        assert set_up_env() is True


def test_set_up_env_false():
    with EnvVars({E2E_SET_UP: 'false'}):
        assert set_up_env() is False


def test_tear_down_env_default_true():
    with EnvVars(ignore=[E2E_TEAR_DOWN]):
        assert tear_down_env() is True


def test_tear_down_env_false():
    with EnvVars({E2E_TEAR_DOWN: 'false'}):
        assert tear_down_env() is False


@pytest.mark.parametrize(
    "attempts,expected_call_count",
    [
        (None, 1),
        (0, 1),
        (1, 1),
        (3, 3),
    ],
)
def test_environment_run_on_failed_conditions(attempts, expected_call_count):
    up = mock.MagicMock()
    down = mock.MagicMock()
    condition = mock.MagicMock()
    condition.side_effect = Exception("exception")

    expected_exception = tenacity.RetryError
    if attempts is None:
        if running_on_ci():
            expected_call_count = 2
        else:
            expected_exception = Exception

    with pytest.raises(expected_exception):
        with environment_run(up=up, down=down, attempts=attempts, conditions=[condition]):
            pass

    assert condition.call_count == expected_call_count


def test_environment_run_condition_failed_only_on_first_run():
    up = mock.MagicMock()
    up.return_value = "{}"
    down = mock.MagicMock()
    condition = mock.MagicMock()
    condition.side_effect = [Exception("exception"), None, None]

    with environment_run(up=up, down=down, attempts=3, conditions=[condition]) as result:
        assert condition.call_count == 2
        assert result == "{}"
