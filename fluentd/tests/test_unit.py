# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.fluentd import Fluentd

from .common import CHECK_NAME


def test_default_timeout(instance):
    # test default timeout
    check = Fluentd(CHECK_NAME, {}, [instance])
    check.check(None)

    assert check.http.options['timeout'] == (5, 5)


def test_init_config_old_timeout(instance):
    # test init_config timeout
    check = Fluentd(CHECK_NAME, {'default_timeout': 2}, [instance])
    check.check(None)
    assert check.http.options['timeout'] == (2, 2)


def test_init_config_timeout(instance):
    # test init_config timeout
    check = Fluentd(CHECK_NAME, {'timeout': 7}, [instance])
    check.check(None)

    assert check.http.options['timeout'] == (7, 7)


def test_instance_old_timeout(instance):
    # test instance default_timeout
    instance['default_timeout'] = 13
    check = Fluentd(CHECK_NAME, {'default_timeout': 9}, [instance])
    check.check(None)

    assert check.http.options['timeout'] == (13, 13)


def test_instance_timeout(instance):
    # test instance timeout
    instance['timeout'] = 15
    check = Fluentd(CHECK_NAME, {}, [instance])
    check.check(None)

    assert check.http.options['timeout'] == (15, 15)
