# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
class SharedConfig(object):
    def __init__(self, **kwargs):
        self.deprecated = kwargs.get('deprecated', '')
        self.timeout = kwargs.get('timeout', 0.0)


class InstanceConfig(object):
    def __init__(self, **kwargs):
        self.array = kwargs.get('array', [])
        self.deprecated = kwargs.get('deprecated', '')
        self.flag = kwargs.get('flag', False)
        self.hyphenated_name = kwargs.get('hyphenated-name', '')
        self.mapping = kwargs.get('mapping', {})
        self.obj = kwargs.get('obj', {})
        self.pass_ = kwargs.get('pass', '')
        self.pid = kwargs.get('pid', 0)
        self.text = kwargs.get('text', '')
        self.timeout = kwargs.get('timeout', 0.0)


class ConfigMixin(object):
    @property
    def config(self):
        # type: () -> InstanceConfig
        return self._config_model_instance

    @property
    def shared_config(self):
        # type: () -> SharedConfig
        return self._config_model_shared
