# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY3

if PY3:
    from .api import ConfigMixin, InstanceConfig, SharedConfig
else:
    from .compat import ConfigMixin, InstanceConfig, SharedConfig
