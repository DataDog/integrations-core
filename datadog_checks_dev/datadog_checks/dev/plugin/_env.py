# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

JMX_TO_INAPP_TYPES = {
    'counter': 'gauge',  # JMX counter -> DSD gauge -> in-app gauge
    'rate': 'gauge',  # JMX rate -> DSD gauge -> in-app gauge
    'monotonic_count': 'rate',  # JMX monotonic_count -> DSD count -> in-app rate
    # TODO: Support JMX histogram
    #       JMX histogram -> DSD histogram -> multiple in-app metrics (max, median, avg, count)
}


def replay_check_run(agent_collector, stub_aggregator, stub_agent):
    errors = []
    for collector in agent_collector:
        aggregator = collector['aggregator']
        inventories = collector.get('inventories')
        runner = collector.get('runner', {})
        check_id = runner.get('CheckID', '')
        check_name = runner.get('CheckName', '')

        if inventories:
            for metadata in inventories.values():
                for meta_key, meta_val in metadata.items():
                    stub_agent.set_check_metadata(check_name, meta_key, meta_val)
        for data in aggregator.get('metrics', []):
            for _, value in data['points']:
                raw_metric_type = data['type']
                if data.get('source_type_name') == 'JMX':
                    raw_metric_type = JMX_TO_INAPP_TYPES.get(raw_metric_type, raw_metric_type)
                metric_type = stub_aggregator.METRIC_ENUM_MAP[raw_metric_type]
                stub_aggregator.submit_metric_e2e(
                    # device is only present when replaying e2e tests. In integration tests it will be a tag
                    check_name,
                    check_id,
                    metric_type,
                    data['metric'],
                    value,
                    data['tags'],
                    data['host'],
                    data.get('device'),
                )

        for data in aggregator.get('service_checks', []):
            stub_aggregator.submit_service_check(
                check_name, check_id, data['check'], data['status'], data['tags'], data['host_name'], data['message']
            )

        if runner.get('LastError'):
            try:
                new_errors = json.loads(runner['LastError'])
            except json.decoder.JSONDecodeError:
                new_errors = [
                    {
                        'message': str(runner['LastError']),
                        'traceback': '',
                    }
                ]
            errors.extend(new_errors)
    if errors:
        raise Exception("\n".join("Message: {}\n{}".format(err['message'], err['traceback']) for err in errors))