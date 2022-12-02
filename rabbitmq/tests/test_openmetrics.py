from datadog_checks.rabbitmq import RabbitMQ


def test_initial_setup(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        (
            "# TYPE rabbitmq_queue_messages_published_total counter\n"
            "# HELP rabbitmq_queue_messages_published_total Total number of messages published to queues\n"
            'rabbitmq_queue_messages_published_total{channel="<0.1043.0>",queue_vhost="/",queue="hello",exchange_vhost="/",exchange=""} 1\n'  # noqa
        )
    )
    check = RabbitMQ(
        "rabbitmq",
        {},
        [{'use_openmetrics': True,"openmetrics_endpoint": "test", "metrics": [".+"], "namespace": "foo"}],
    )
    dd_run_check(check)

    aggregator.assert_metric(
        "rabbitmq.rabbitmq_queue_messages_published.count",
        1,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=["endpoint:test", 'channel:<0.1043.0>', 'exchange:', 'exchange_vhost:/', 'queue:hello', 'queue_vhost:/'],
    )
