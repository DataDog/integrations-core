# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from prometheus_client.parser import text_string_to_metric_families

from datadog_checks.base import OpenMetricsBaseCheckV2

SERVICES = ('checkout', 'catalog', 'payments', 'fulfillment', 'search')
REGIONS = ('us-east-1', 'us-west-2', 'eu-central-1', 'ap-southeast-1')
METHODS = ('GET', 'POST', 'PUT', 'DELETE')
STATUS_CLASSES = ('2xx', '3xx', '4xx', '5xx')
CONSUMERS = tuple(f'consumer-{i:02d}' for i in range(12))


def make_labels(index, shape='current'):
    if shape == 'none':
        return {'sample': str(index)}
    if shape == 'two':
        return {
            'service': SERVICES[index % len(SERVICES)],
            'region': REGIONS[index % len(REGIONS)],
        }
    if shape == 'high':
        return {
            'service': SERVICES[index % len(SERVICES)],
            'region': REGIONS[index % len(REGIONS)],
            'method': METHODS[index % len(METHODS)],
            'status_class': STATUS_CLASSES[index % len(STATUS_CLASSES)],
            'route': f'/api/v2/resource/{index:04d}',
            'consumer': f'consumer-{index:04d}',
            'pod': f'pod-{index:04d}',
            'instance': f'10.0.{index // 256}.{index % 256}:9100',
        }
    return {
        'service': SERVICES[index % len(SERVICES)],
        'region': REGIONS[index % len(REGIONS)],
        'method': METHODS[index % len(METHODS)],
        'status_class': STATUS_CLASSES[index % len(STATUS_CLASSES)],
        'route': f'/api/v1/resource/{index % 60:02d}',
        'consumer': CONSUMERS[index % len(CONSUMERS)],
    }


def format_labels(labels):
    return ','.join(f'{name}="{value}"' for name, value in labels.items())


def make_payload(samples=962, families=1, label_shape='current'):
    lines = [
        '# HELP target_info Synthetic target identity.',
        '# TYPE target_info gauge',
        'target_info{job="openmetrics_hotpath_bench"} 1',
    ]
    sample_count = samples - 1
    per_family = sample_count // families
    remainder = sample_count % families
    sample_index = 0
    for family_index in range(families):
        metric = f'om_hotpath_family_{family_index:04d}' if families > 1 else 'om_hotpath_gauge'
        lines.append(f'# HELP {metric} Synthetic gauge.')
        lines.append(f'# TYPE {metric} gauge')
        count = per_family + (1 if family_index < remainder else 0)
        for _ in range(count):
            labels = make_labels(sample_index, label_shape)
            lines.append(f'{metric}{{{format_labels(labels)}}} {sample_index % 997}')
            sample_index += 1
    lines.append('')
    return '\n'.join(lines)


def parse_payload(payload):
    return list(text_string_to_metric_families(payload))


def check_for_payload(metrics=None):
    check = OpenMetricsBaseCheckV2(
        'test',
        {},
        [
            {
                'openmetrics_endpoint': 'foo',
                'namespace': 'hotpath',
                'metrics': metrics or ['.*'],
                'max_returned_metrics': 10000,
            }
        ],
    )
    check.configure_scrapers()
    return check


def run_parsed_metrics(check, metrics):
    scraper = check.scrapers['foo']
    runtime_data = {'flush_first_value': True, 'static_tags': scraper.static_tags}
    for metric in metrics:
        transformer = scraper.metric_transformer.get(metric)
        if transformer is not None:
            transformer(metric, scraper.generate_sample_data(metric), runtime_data)


def run_parsed_metrics_cold(metrics):
    check = check_for_payload()
    run_parsed_metrics(check, metrics)


def run_parsed_metrics_cold_scrapers(metrics, scraper_count=25):
    for _ in range(scraper_count):
        check = check_for_payload()
        run_parsed_metrics(check, metrics)


def run_transformer_get(check, metrics):
    scraper = check.scrapers['foo']
    for metric in metrics:
        scraper.metric_transformer.get(metric)


def run_transformer_get_cold(metrics):
    check = check_for_payload()
    run_transformer_get(check, metrics)


def bench_full_check(benchmark, dd_run_check, mock_http_response, payload, metrics=None):
    mock_http_response(payload)
    check = OpenMetricsBaseCheckV2(
        'test',
        {},
        [
            {
                'openmetrics_endpoint': 'foo',
                'namespace': 'hotpath',
                'metrics': metrics or ['.*'],
                'max_returned_metrics': 10000,
            }
        ],
    )
    dd_run_check(check)
    benchmark(check.check, None)


def test_hotpath_parse_one_family_two_labels(benchmark):
    payload = make_payload(samples=962, families=1, label_shape='two')
    benchmark(parse_payload, payload)


def test_hotpath_parse_current_labels(benchmark):
    payload = make_payload(samples=962, families=1, label_shape='current')
    benchmark(parse_payload, payload)


def test_hotpath_parse_high_labels(benchmark):
    payload = make_payload(samples=962, families=1, label_shape='high')
    benchmark(parse_payload, payload)


def test_hotpath_parse_many_families(benchmark):
    payload = make_payload(samples=962, families=960, label_shape='two')
    benchmark(parse_payload, payload)


def test_hotpath_transform_current_labels(benchmark):
    payload = make_payload(samples=962, families=1, label_shape='current')
    metrics = parse_payload(payload)
    check = check_for_payload()
    benchmark(run_parsed_metrics, check, metrics)


def test_hotpath_transform_high_labels(benchmark):
    payload = make_payload(samples=962, families=1, label_shape='high')
    metrics = parse_payload(payload)
    check = check_for_payload()
    benchmark(run_parsed_metrics, check, metrics)


def test_hotpath_transform_many_families(benchmark):
    payload = make_payload(samples=962, families=960, label_shape='two')
    metrics = parse_payload(payload)
    check = check_for_payload()
    benchmark(run_parsed_metrics, check, metrics)


def test_hotpath_transformer_get_cold_many_families(benchmark):
    payload = make_payload(samples=962, families=960, label_shape='two')
    metrics = parse_payload(payload)
    benchmark(run_transformer_get_cold, metrics)


def test_hotpath_transformer_get_warm_many_families(benchmark):
    payload = make_payload(samples=962, families=960, label_shape='two')
    metrics = parse_payload(payload)
    check = check_for_payload()
    run_transformer_get(check, metrics)
    benchmark(run_transformer_get, check, metrics)


def test_hotpath_transform_cold_one_family_two_labels(benchmark):
    payload = make_payload(samples=962, families=1, label_shape='two')
    metrics = parse_payload(payload)
    benchmark(run_parsed_metrics_cold, metrics)


def test_hotpath_transform_cold_current_labels(benchmark):
    payload = make_payload(samples=962, families=1, label_shape='current')
    metrics = parse_payload(payload)
    benchmark(run_parsed_metrics_cold, metrics)


def test_hotpath_transform_cold_many_families(benchmark):
    payload = make_payload(samples=962, families=960, label_shape='two')
    metrics = parse_payload(payload)
    benchmark(run_parsed_metrics_cold, metrics)


def test_hotpath_transform_cold_many_families_multi_scraper(benchmark):
    payload = make_payload(samples=962, families=960, label_shape='two')
    metrics = parse_payload(payload)
    benchmark(run_parsed_metrics_cold_scrapers, metrics)


def test_hotpath_full_one_family_two_labels(benchmark, dd_run_check, mock_http_response):
    payload = make_payload(samples=962, families=1, label_shape='two')
    bench_full_check(benchmark, dd_run_check, mock_http_response, payload)


def test_hotpath_full_current_labels(benchmark, dd_run_check, mock_http_response):
    payload = make_payload(samples=962, families=1, label_shape='current')
    bench_full_check(benchmark, dd_run_check, mock_http_response, payload)


def test_hotpath_full_high_labels(benchmark, dd_run_check, mock_http_response):
    payload = make_payload(samples=962, families=1, label_shape='high')
    bench_full_check(benchmark, dd_run_check, mock_http_response, payload)


def test_hotpath_full_many_families(benchmark, dd_run_check, mock_http_response):
    payload = make_payload(samples=962, families=960, label_shape='two')
    bench_full_check(benchmark, dd_run_check, mock_http_response, payload)
