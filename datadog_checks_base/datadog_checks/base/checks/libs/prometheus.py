# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from prometheus_client.metrics_core import Metric
from prometheus_client.parser import _parse_sample, _replace_help_escaping


# This copies most of the code from upstream at that version:
# https://github.com/prometheus/client_python/blob/049744296d216e6be65dc8f3d44650310f39c384/prometheus_client/parser.py#L144
# but reverting the behavior to a compatible version, which doesn't change counters to have a total suffix. See
# https://github.com/prometheus/client_python/commit/a4dd93bcc6a0422e10cfa585048d1813909c6786#diff-0adf47ea7f99c66d4866ccb4e557a865L158
def text_fd_to_metric_families(fd):
    """Parse Prometheus text format from a file descriptor.

    This is a laxer parser than the main Go parser, so successful parsing does
    not imply that the parsed text meets the specification.

    Yields Metric's.
    """
    name = ''
    documentation = ''
    typ = 'untyped'
    samples = []
    allowed_names = []

    def build_metric(name, documentation, typ, samples):
        # This is where the change is happening: we don't munge counters as upstream does.
        metric = Metric(name, documentation, typ)
        metric.samples = samples
        return metric

    for line in fd:
        line = line.strip()

        if line.startswith('#'):
            parts = line.split(None, 3)
            if len(parts) < 2:
                continue
            if parts[1] == 'HELP':
                if parts[2] != name:
                    if name != '':
                        yield build_metric(name, documentation, typ, samples)
                    # New metric
                    name = parts[2]
                    typ = 'untyped'
                    samples = []
                    allowed_names = [parts[2]]
                if len(parts) == 4:
                    documentation = _replace_help_escaping(parts[3])
                else:
                    documentation = ''
            elif parts[1] == 'TYPE':
                if parts[2] != name:
                    if name != '':
                        yield build_metric(name, documentation, typ, samples)
                    # New metric
                    name = parts[2]
                    documentation = ''
                    samples = []
                typ = parts[3]
                allowed_names = {
                    'counter': [''],
                    'gauge': [''],
                    'summary': ['_count', '_sum', ''],
                    'histogram': ['_count', '_sum', '_bucket'],
                }.get(typ, [''])
                allowed_names = [name + n for n in allowed_names]
            else:
                # Ignore other comment tokens
                pass
        elif line == '':
            # Ignore blank lines
            pass
        else:
            sample = _parse_sample(line)
            if sample.name not in allowed_names:
                if name != '':
                    yield build_metric(name, documentation, typ, samples)
                # New metric, yield immediately as untyped singleton
                name = ''
                documentation = ''
                typ = 'untyped'
                samples = []
                allowed_names = []
                yield build_metric(sample[0], documentation, typ, [sample])
            else:
                samples.append(sample)

    if name != '':
        yield build_metric(name, documentation, typ, samples)
