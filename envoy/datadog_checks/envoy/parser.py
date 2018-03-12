from .errors import UnknownMetric
from .metrics import METRIC_PREFIX, METRIC_TREE, METRICS


def parse_metric(metric):
    """Takes a metric formatted by Envoy and splits it into a unique
    metric name. Returns the unique metric name, a list of tags, and
    the name of the submission method.

    Example:
        'listener.0.0.0.0_80.downstream_cx_total' ->
        ('listener.downstream_cx_total', ['address:0.0.0.0:80'], 'count')
    """
    metric_parts = []
    tag_values = []
    mapping = METRIC_TREE

    for metric_part in metric.split('.'):
        if metric_part in mapping:
            metric_parts.append(metric_part)
            mapping = mapping[metric_part]
        else:
            tag_values.append(metric_part)

    metric = '.'.join(metric_parts)
    if metric not in METRICS:
        raise UnknownMetric

    tag_names = METRICS[metric]['tags']
    if len(tag_values) != len(tag_names):
        tag_values = reassemble_addresses(tag_values)

        if len(tag_values) != len(tag_names):
            raise UnknownMetric

    tags = [
        '{}:{}'.format(tag_name, tag_value)
        for tag_name, tag_value in zip(tag_names, tag_values)
    ]

    return METRIC_PREFIX + metric, tags, METRICS[metric]['method']


def reassemble_addresses(seq):
    """Takes a sequence of strings and combines any sub-sequence that looks
    like an IPv4 address into a single string.

    Example:
        ['listener', '0', '0', '0', '0_80', downstream_cx_total'] ->
        ['listener', '0.0.0.0:80', 'downstream_cx_total']
    """
    reassembled = []
    prev = ''

    for s in seq:
        if prev.isdigit():
            try:
                end, port = s.split('_')
            except ValueError:
                end, port = '', ''

            if s.isdigit():
                reassembled[-1] += '.{}'.format(s)
            elif end.isdigit() and port.isdigit():
                reassembled[-1] += '.{}:{}'.format(end, port)
            else:
                reassembled.append(s)
        else:
            reassembled.append(s)

        prev = s

    return reassembled
