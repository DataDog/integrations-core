# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
try:
    import orjson as json
except ImportError:
    import json


__all__ = ['json']
