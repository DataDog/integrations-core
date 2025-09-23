# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def test_generate_metrics(fake_repo, ddev, mocker):
    mocker.patch('time.sleep', side_effect=KeyboardInterrupt)

    submit_metrics_mock = mocker.patch('datadog_api_client.v2.api.metrics_api.MetricsApi.submit_metrics')

    ddev('meta', 'scripts', 'generate-metrics', 'dummy', '--api-key', '1234')

    assert submit_metrics_mock.call_count == 1

    payload = submit_metrics_mock.call_args_list[0][1]
    assert len(payload['body']['series']) == 1
    assert payload['body']['series'][0]['metric'] == 'dummy.metric'
