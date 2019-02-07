# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import os
import re
import shlex
import subprocess

import pytest

from . import common
from datadog_checks.base import ensure_unicode
from datadog_checks.varnish import Varnish


pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator):
    check = Varnish(common.CHECK_NAME, {}, {})
    config = common.get_config_by_version()

    check.check(config)
    for mname in common.COMMON_METRICS:
        aggregator.assert_metric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])


@pytest.mark.usefixtures('dd_environment')
def test_inclusion_filter(aggregator):
    check = Varnish(common.CHECK_NAME, {}, {})
    config = common.get_config_by_version()
    config['metrics_filter'] = ['SMA.*']

    check.check(config)
    for mname in common.COMMON_METRICS:
        if 'SMA.' in mname:
            aggregator.assert_metric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])
        else:
            aggregator.assert_metric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])


@pytest.mark.usefixtures('dd_environment')
def test_exclusion_filter(aggregator):
    check = Varnish(common.CHECK_NAME, {}, {})
    config = common.get_config_by_version()
    config['metrics_filter'] = ['^SMA.Transient.c_req']

    check.check(config)
    for mname in common.COMMON_METRICS:
        if 'SMA.Transient.c_req' in mname:
            aggregator.assert_metric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])
        elif 'varnish.uptime' not in mname:
            aggregator.assert_metric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])


def test_version():
    """
    If the docker image is in a different repository, we check that the
    version requested in the VARNISH_VERSION env var is the one running inside the container.
    """
    varnishstat = common.get_varnish_stat_path()

    # Version info is printed to stderr
    output = subprocess.check_output(shlex.split(varnishstat) + ["-V"], stderr=subprocess.STDOUT)
    res = re.search(r"varnish-(\d+\.\d\.\d)", ensure_unicode(output))
    if res is None:
        raise Exception("Could not retrieve varnish version from docker")

    version = res.groups()[0]
    assert version == os.environ.get('VARNISH_VERSION', common.VARNISH_DEFAULT_VERSION)
