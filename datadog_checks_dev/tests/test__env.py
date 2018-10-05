# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import EnvVars
from datadog_checks.dev._env import E2E_SET_UP, E2E_TEAR_DOWN, set_up_env, tear_down_env


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
