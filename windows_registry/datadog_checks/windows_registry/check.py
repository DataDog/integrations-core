# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import winreg
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck, ConfigurationError  # noqa: F401

HIVE_MAP = {
    'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
    'HKLM': winreg.HKEY_LOCAL_MACHINE,
    'HKEY_USERS': winreg.HKEY_USERS,
    'HKU': winreg.HKEY_USERS,
    'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
    'HKCU': winreg.HKEY_CURRENT_USER,
}


class WindowsRegistryCheck(AgentCheck):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'windows_registry'

    def __init__(self, name, init_config, instances):
        super(WindowsRegistryCheck, self).__init__(name, init_config, instances)

    def check(self, instance):
        keypath = instance.get('keypath')
        if not keypath:
            raise ConfigurationError('Missing keypath')
        split_keypath = re.split(r'\\|/', keypath)
        if len(split_keypath) < 2:
            raise ConfigurationError('Invalid registry path')
        if split_keypath[0] in HIVE_MAP:
            subkeypath = '\\'.join(split_keypath[1:])
            key = winreg.OpenKey(HIVE_MAP[split_keypath[0]], subkeypath)
            for keyname, _metric_name, _metric_type in instance['metrics']:
                value = winreg.QueryValueEx(key, keyname)
                if _metric_type == 'gauge':
                    if value[1] == winreg.REG_DWORD:
                        self.gauge(f'win_registry.{_metric_name}', value[0])
            winreg.CloseKey(key)
        else:
            raise ConfigurationError(f'Configuration error, unknown hive {split_keypath[0]}')
