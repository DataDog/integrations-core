# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from typing import Any

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS

from .common import INSTANCE, build_lab_instance
from .fake_panos import FakePanos


@pytest.fixture(scope='session')
def dd_environment():
    if os.environ.get('USE_PANOS_LAB'):
        # Lab mode: one instance built from environment variables only, no docker fakes. Set the variables in
        # your own terminal (the password is read silently and never written to a file or to the shell history):
        #
        #   read -rs "PANOS_PASSWORD?Password: "
        #   export PANOS_PASSWORD PANOS_LAB_HOSTS=<ip1>,<ip2> PANOS_LAB_USERNAME=<username>
        #
        # then run `ddev env start pan_firewall py3.13-lab`, `ddev env agent pan_firewall py3.13-lab check` and
        # `ddev env test pan_firewall py3.13-lab`. The instance is never logged or printed: it holds the password.
        #
        # Panorama mode (setting PANOS_LAB_PANORAMA_HOST selects it, and PANOS_LAB_HOSTS is then not needed): the
        # firewalls are discovered from Panorama, so set its host and credentials, plus the firewalls' own. Read
        # BOTH passwords silently, in your own terminal:
        #
        #   read -rs "PANOS_LAB_PANORAMA_PASSWORD?Panorama password: "
        #   read -rs "PANOS_PASSWORD?Firewall password: "
        #   export PANOS_LAB_PANORAMA_PASSWORD PANOS_PASSWORD
        #   export PANOS_LAB_PANORAMA_HOST=<host> PANOS_LAB_PANORAMA_USERNAME=<username> PANOS_LAB_USERNAME=<username>
        #   export PANOS_LAB_FIREWALL_OVERRIDES=<serial>=<reachable-ip>,<serial>=<reachable-ip>
        #
        # PANOS_LAB_FIREWALL_OVERRIDES is only needed when the IPs Panorama reports are not reachable from where the
        # Agent runs. Then run the `lab-panorama` env (its own name: hatch cannot make one env depend on either of
        # two variables):
        #
        #   ddev env start pan_firewall py3.13-lab-panorama
        #   ddev env test pan_firewall py3.13-lab-panorama
        #   ddev env stop pan_firewall py3.13-lab-panorama
        yield {'instances': [build_lab_instance()]}
    else:
        # The docker environment is added in a later task.
        yield


@pytest.fixture
def instance() -> dict[str, Any]:
    return copy.deepcopy(INSTANCE)


@pytest.fixture(autouse=True)
def fake_panos(monkeypatch, datadog_agent) -> FakePanos:
    """Serve every HTTP POST from the fake PAN-OS API, so no unit test reaches the network.

    Requesting `datadog_agent` resets the stubbed persistent cache between tests.
    """
    fake = FakePanos()
    monkeypatch.setattr(RequestsWrapper, 'post', lambda _self, url, **options: fake.post(url, **options))
    return fake


@pytest.fixture
def real_collectors():
    """Request it to keep the real collectors registered, which the other tests replace with stubs."""


@pytest.fixture(autouse=True)
def only_test_collectors(request, monkeypatch):
    """Start every test with an empty collector registry, so a test runs the collectors it registers and no others."""
    if 'real_collectors' not in request.fixturenames:
        for name in list(COLLECT_FUNCTIONS):
            monkeypatch.delitem(COLLECT_FUNCTIONS, name)
