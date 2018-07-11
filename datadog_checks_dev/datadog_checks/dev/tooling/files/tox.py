# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE = """\
[tox]
minversion = 2.0
basepython = py27
envlist =
    {check_name}
    flake8

[testenv]
platform = linux|darwin|win32
deps =
    ../datadog_checks_base
    -r../datadog_checks_base/requirements.in
    -rrequirements-dev.txt
passenv =
    DOCKER*
    COMPOSE*
commands =
    pip install --require-hashes -r requirements.txt
    pytest -v

[testenv:{check_name}]

[testenv:flake8]
skip_install = true
deps = flake8
commands = flake8 .

[flake8]
exclude = .eggs,.tox,build
max-line-length = 120
"""


class Tox(File):
    def __init__(self, config):
        super(Tox, self).__init__(
            os.path.join(config['root'], 'tox.ini'),
            TEMPLATE.format(
                check_name=config['check_name'],
            )
        )
