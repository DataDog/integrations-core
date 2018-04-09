# (C) Datadog, Inc. 2012-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import os
import subprocess
import requests
import time
import logging

from datadog_checks.haproxy import HAProxy

import common

@pytest.mark.integration
def test_check(aggregator, spin_up_haproxy):
    haproxy_check = HAProxy(CHECK_NAME, {}, {})
    assert True
