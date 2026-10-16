# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from .common import build_lab_instance
from .helpers import new_check

PASSWORD = 'lab-password-must-not-leak'
PANORAMA_PASSWORD = 'panorama-password-must-not-leak'
STATIC_ENV = {
    'PANOS_LAB_MODE': 'static',
    'PANOS_LAB_HOSTS': '192.0.2.10',
    'PANOS_LAB_USERNAME': 'lab-user',
    'PANOS_PASSWORD': PASSWORD,
}
PANORAMA_ENV = {
    'PANOS_LAB_MODE': 'panorama',
    'PANOS_LAB_PANORAMA_HOST': 'panorama.example.com',
    'PANOS_LAB_PANORAMA_USERNAME': 'panorama-user',
    'PANOS_LAB_PANORAMA_PASSWORD': PANORAMA_PASSWORD,
    'PANOS_LAB_USERNAME': 'lab-user',
    'PANOS_PASSWORD': PASSWORD,
}


@pytest.mark.parametrize(
    'environ, secrets',
    [
        pytest.param(STATIC_ENV, (PASSWORD,), id='static'),
        pytest.param(PANORAMA_ENV, (PASSWORD, PANORAMA_PASSWORD), id='panorama'),
    ],
)
def test_lab_password_never_leaks(caplog, aggregator, environ, secrets):
    # An explicit mapping, never the real environment: a lab variable exported in the developer's shell must not
    # change which mode (or whose password) this test builds.
    check = new_check(build_lab_instance(environ))
    with caplog.at_level(logging.DEBUG):
        assert check.run() == ''

    # Not `repr(check.config)`: generated pydantic models keep secrets as plain `str`, so it shows the password.
    # That is true of every integration, and the check never logs or prints its config.
    exposed = {'log': caplog.text, 'check': repr(check), 'check str': str(check)}
    leaks = [(name, secret) for name, text in exposed.items() for secret in secrets if secret in text]
    assert leaks == []
