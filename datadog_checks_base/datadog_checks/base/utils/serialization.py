"""
This module is deprecated and will begin emitting deprecation warnings after all official
integrations have migrated to the new `datadog_checks.base.utils.format.json` module.
"""

# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

try:
    import orjson as json

    impl = 'orjson'
    sort_keys_kwargs = {'option': json.OPT_SORT_KEYS}

    def from_json(s, **kwargs):
        return json.loads(s, **kwargs)

    def to_json(d, **kwargs):
        return json.dumps(d, **kwargs).decode()

except ImportError:
    import json

    impl = 'stdlib'
    sort_keys_kwargs = {'sort_keys': True}

    def from_json(s, **kwargs):
        return json.loads(s, **kwargs)

    def to_json(d, **kwargs):
        return json.dumps(d, **kwargs)


logger = logging.getLogger(__name__)
logger.debug('Using JSON implementation from %s', impl)

__all__ = ['from_json', 'json', 'sort_keys_kwargs', 'to_json']
