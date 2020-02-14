# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import binary_type, text_type


def is_primitive(obj):
    # https://github.com/python/cpython/blob/4f82a53c5d34df00bf2d563c2417f5e2638d1004/Lib/json/encoder.py#L357-L377
    return obj is None or isinstance(obj, (binary_type, bool, float, int, text_type))


def is_metadata_collection_enabled(func):
    """
    Use this decorator to avoid making unnecesary api calls when metadata collection is disabled
    :param func:
    :return:
    """
    def _decorator(self, *args, **kwargs):
        if self.agentConfig.get('enable_metadata_collection', True):
            return func(self, *args, **kwargs)
    return _decorator
