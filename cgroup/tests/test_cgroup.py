# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import mock

# 3p
from docker import Client
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest
from tests.checks.common import load_check

log = logging.getLogger('tests')

@attr(requires='cgroup')
class TestCheckCgroup(AgentCheckTest):
    """Basic Test for cgroup integration."""
    CHECK_NAME = 'cgroup'

    ## TODO