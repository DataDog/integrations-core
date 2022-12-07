# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import transformers

NATIVE_TRANSFORMERS = {
    'count': transformers.get_count,
    'gauge': transformers.get_gauge,
    'monotonic_count': transformers.get_monotonic_count,
    'rate': transformers.get_rate,
}
TRANSFORMERS = {
    'service_check': transformers.get_service_check,
    'temporal_percent': transformers.get_temporal_percent,
    'time_elapsed': transformers.get_time_elapsed,
}
TRANSFORMERS.update(NATIVE_TRANSFORMERS)


# For documentation generation
class Transformers(object):
    pass


for transformer_name, transformer_factory in sorted(TRANSFORMERS.items()):
    setattr(Transformers, transformer_name, transformer_factory)
