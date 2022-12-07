from datadog_checks.envoy.metrics import METRIC_PREFIX, METRIC_TREE, METRICS
from datadog_checks.envoy.utils import make_metric_tree


def test_metric_prefix():
    assert METRIC_PREFIX == 'envoy.'


def test_metric_tags_sequence_type():
    for metric in METRICS:
        for tag in METRICS[metric]['tags']:
            assert isinstance(tag, tuple)


def test_metric_tags_length():
    for metric in METRICS:
        assert len(metric.split('.')) == len(METRICS[metric]['tags'])


def test_metric_tree():
    assert METRIC_TREE == make_metric_tree(METRICS)
