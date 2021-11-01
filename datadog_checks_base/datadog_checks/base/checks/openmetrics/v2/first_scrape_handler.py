# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def first_scrape_handler(metrics, runtime_data, agent_start_time):
    process_start_time = None
    metrics_buffer = []
    metrics_with_counters = {"counter", "histogram", "summary"}

    for metric in metrics:
        if metric.name == 'process_start_time_seconds' and metric.samples:
            min_metric_value = min(s.value for s in metric.samples)
            if process_start_time is None or min_metric_value < process_start_time:
                process_start_time = min_metric_value

        if metric.type in metrics_with_counters:
            metrics_buffer.append(metric)
            continue

        yield metric

    if process_start_time is not None and agent_start_time is not None and process_start_time > agent_start_time:
        runtime_data['flush_first_value'] = True

    yield from metrics_buffer
