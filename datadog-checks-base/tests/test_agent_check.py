# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.checks import AgentCheck

def test_instance():
    """
    Simply assert the class can be insantiated
    """
    AgentCheck()
