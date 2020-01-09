# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks import config


def test_alias():
    """
    Ensure we have an alias to import is_affirmative as _is_affirmative for
    backward compatibility with Agent 5.x
    """
    assert getattr(config, "_is_affirmative", None) is not None


def test_is_affirmative():
    assert config.is_affirmative(None) is False
    assert config.is_affirmative(0) is False
    assert config.is_affirmative("whatever, it could be 'off'") is False

    assert config.is_affirmative(1) is True
    assert config.is_affirmative('YES') is True
    assert config.is_affirmative('True') is True
    assert config.is_affirmative('On') is True
    assert config.is_affirmative('1') is True
