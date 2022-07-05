# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import os
import platform
import sys


def get_os():
    """
    Human-friendly OS name
    """
    if sys.platform == 'darwin':
        return 'mac'
    elif sys.platform.find('freebsd') != -1:
        return 'freebsd'
    elif sys.platform.find('linux') != -1:
        return 'linux'
    elif sys.platform.find('win32') != -1:
        return 'windows'
    elif sys.platform.find('sunos') != -1:
        return 'solaris'
    else:
        return sys.platform


class Platform(object):
    """
    Return information about the given platform.
    """

    @staticmethod
    def is_darwin(name=None):
        name = name or sys.platform
        return platform.system() == 'Darwin' or 'darwin' in name

    @staticmethod
    def is_mac(name=None):
        return Platform.is_darwin(name)

    @staticmethod
    def is_freebsd(name=None):
        name = name or sys.platform
        return name.startswith("freebsd")

    @staticmethod
    def is_linux(name=None):
        name = name or sys.platform
        return platform.system() == 'Linux' or 'linux' in name

    @staticmethod
    def is_bsd(name=None):
        """Return true if this is a BSD like operating system."""
        name = name or sys.platform
        return Platform.is_darwin(name) or Platform.is_freebsd(name)

    @staticmethod
    def is_solaris(name=None):
        name = name or sys.platform
        return name == "sunos5"

    @staticmethod
    def is_unix(name=None):
        """Return true if the platform is a unix, False otherwise."""
        name = name or sys.platform
        return Platform.is_darwin(name) or Platform.is_linux(name) or Platform.is_freebsd(name)

    @staticmethod
    def is_win32(name=None):
        name = name or sys.platform
        return platform.system() == 'Windows' or name == 'win32'

    @staticmethod
    def is_windows(name=None):
        return Platform.is_win32(name)

    @staticmethod
    def python_architecture():
        if sys.maxsize > 2**32:
            return "64bit"
        else:
            return "32bit"

    @staticmethod
    def is_ecs_instance():
        from utils.dockerutil import DockerUtil

        return DockerUtil().is_ecs()

    @staticmethod
    def is_containerized():
        return 'DOCKER_DD_AGENT' in os.environ

    @staticmethod
    def is_k8s():
        return 'KUBERNETES_PORT' in os.environ
