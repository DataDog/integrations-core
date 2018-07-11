# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE_NAMESPACE = """\
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
"""

TEMPLATE_ABOUT = """\

__version__ = '0.0.1'
"""

TEMPLATE_INIT = """\
from .__about__ import __version__
from .{check_name} import {check_class}

__all__ = [
    '__version__',
    '{check_class}'
]
"""

TEMPLATE_CHECK = """\
from datadog_checks.checks import AgentCheck


class {check_class}(AgentCheck):
    def check(self, instance):
        pass
"""


class PackageNamespace(File):
    def __init__(self, config):
        super(PackageNamespace, self).__init__(
            os.path.join(config['root'], 'datadog_checks', '__init__.py'),
            TEMPLATE_NAMESPACE
        )


class PackageAbout(File):
    def __init__(self, config):
        super(PackageAbout, self).__init__(
            os.path.join(config['root'], 'datadog_checks', config['check_name'], '__about__.py'),
            TEMPLATE_ABOUT
        )


class PackageInit(File):
    def __init__(self, config):
        super(PackageInit, self).__init__(
            os.path.join(config['root'], 'datadog_checks', config['check_name'], '__init__.py'),
            TEMPLATE_INIT.format(
                check_name=config['check_name'],
                check_class=config['check_class'],
            )
        )


class PackageCheck(File):
    def __init__(self, config):
        super(PackageCheck, self).__init__(
            os.path.join(config['root'], 'datadog_checks', config['check_name'], '{}.py'.format(config['check_name'])),
            TEMPLATE_CHECK.format(
                check_class=config['check_class'],
            )
        )
