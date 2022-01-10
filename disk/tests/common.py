# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.docker import using_windows_containers
from datadog_checks.dev.utils import ON_WINDOWS

HERE = os.path.dirname(os.path.abspath(__file__))

if ON_WINDOWS:
    DEFAULT_DEVICE_NAME = 'c:'
    DEFAULT_DEVICE_BASE_NAME = 'c:'
    DEFAULT_FILE_SYSTEM = 'ntfs'
    DEFAULT_MOUNT_POINT = 'c:'
else:
    DEFAULT_DEVICE_NAME = '/dev/sda1'
    DEFAULT_DEVICE_BASE_NAME = 'sda1'
    DEFAULT_FILE_SYSTEM = 'ext4'
    DEFAULT_MOUNT_POINT = '/'

E2E_METADATA = {'docker_platform': 'windows' if using_windows_containers() else 'linux'}
