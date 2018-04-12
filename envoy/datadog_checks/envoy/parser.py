from .errors import UnknownMetric
from .metrics import METRIC_PREFIX, METRIC_TREE, METRICS


def parse_metric(metric):
    """Takes a metric formatted by Envoy and splits it into a unique
    metric name. Returns the unique metric name, a list of tags, and
    the name of the submission method.

    Example:
        'listener.0.0.0.0_80.downstream_cx_total' ->
        ('listener.downstream_cx_total', ['address:0.0.0.0_80'], 'count')
    """
    metric_mapping = METRIC_TREE
    metric_parts = []
    tag_values = []
    tag_builder = []

    for metric_part in metric.split('.'):
        if metric_part in metric_mapping:
            metric_parts.append(metric_part)
            metric_mapping = metric_mapping[metric_part]

            # Rebuild any built up tags anytime we encounter a known metric part
            if tag_builder:
                tag_values.append('.'.join(tag_builder))
                del tag_builder[:]
        else:
            tag_builder.append(metric_part)

    # Rebuild any trailing tags
    if tag_builder:
        tag_values.append('.'.join(tag_builder))
        del tag_builder[:]

    metric = '.'.join(metric_parts)
    if metric not in METRICS:
        raise UnknownMetric

    tag_names = METRICS[metric]['tags']
    print(tag_names)
    print(tag_values)
    print(tag_builder)
    if len(tag_values) != len(tag_names):
        raise UnknownMetric

    tags = [
        '{}:{}'.format(tag_name, tag_value)
        for tag_name, tag_value in zip(tag_names, tag_values)
    ]

    return METRIC_PREFIX + metric, tags, METRICS[metric]['method']
