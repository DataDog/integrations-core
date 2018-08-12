# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File


class TestInit(File):
    def __init__(self, config):
        super(TestInit, self).__init__(
            os.path.join(config['root'], 'tests', '__init__.py'),
        )


class TestCheck(File):
    def __init__(self, config):
        super(TestCheck, self).__init__(
            os.path.join(config['root'], 'tests', 'test_{}.py'.format(config['check_name'])),
        )


class TestConf(File):
    def __init__(self, config):
        super(TestConf, self).__init__(
            os.path.join(config['root'], 'tests', 'conftest.py'),
        )
