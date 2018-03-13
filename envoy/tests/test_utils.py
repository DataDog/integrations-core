from datadog_checks.envoy.utils import make_metric_tree


def test_make_metric_tree():
    metrics = {
        'http.admin.downstream_cx_total': '',
        'http.admin.rs_too_large': '',
    }

    assert make_metric_tree(metrics) == {
        'http': {
            'admin': {
                'downstream_cx_total': {},
                'rs_too_large': {},
            },
        },
    }
