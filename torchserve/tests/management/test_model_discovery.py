# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.torchserve.model_discovery import ModelDiscovery

from ..common import get_fixture_path

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'expected_models, fixture_folder, status_codes',
    [
        pytest.param(
            [],
            "no_models",
            [200],
            id="1 page, no model",
        ),
        pytest.param(
            [
                {"modelName": "linear_regression_1_1", "modelUrl": "linear_regression_1_1.mar"},
                {"modelName": "linear_regression_1_2", "modelUrl": "linear_regression_1_2_v3.mar"},
            ],
            "1_page",
            [200],
            id="1 page, 2 models",
        ),
        pytest.param(
            [
                {
                    "modelName": "linear_regression_1_1",
                    "modelUrl": "linear_regression_1_1.mar",
                },
                {
                    "modelName": "linear_regression_1_2",
                    "modelUrl": "linear_regression_1_2_v3.mar",
                },
                {
                    "modelName": "linear_regression_2_2",
                    "modelUrl": "linear_regression_2_2.mar",
                },
                {
                    "modelName": "linear_regression_2_3",
                    "modelUrl": "linear_regression_2_3.mar",
                },
                {
                    "modelName": "linear_regression_3_2",
                    "modelUrl": "linear_regression_3_2.mar",
                },
            ],
            "3_pages",
            [200, 200, 200],
            id="3 pages, 5 models",
        ),
        pytest.param(
            [],
            "3_pages",
            [500],
            id="3 pages, fail on first call",
        ),
        pytest.param(
            [
                {"modelName": "linear_regression_1_1", "modelUrl": "linear_regression_1_1.mar"},
                {"modelName": "linear_regression_1_2", "modelUrl": "linear_regression_1_2_v3.mar"},
            ],
            "3_pages",
            [200, 500],
            id="3 pages, fail on second call",
        ),
        pytest.param(
            [
                {"modelName": "linear_regression_1_1", "modelUrl": "linear_regression_1_1.mar"},
                {"modelName": "linear_regression_1_2", "modelUrl": "linear_regression_1_2_v3.mar"},
                {
                    "modelName": "linear_regression_2_2",
                    "modelUrl": "linear_regression_2_2.mar",
                },
                {
                    "modelName": "linear_regression_2_3",
                    "modelUrl": "linear_regression_2_3.mar",
                },
            ],
            "3_pages",
            [200, 200, 500],
            id="3 pages, fail on last call",
        ),
    ],
)
def test_get_models(
    fake_http, fake_http_response, check, mocked_management_instance, expected_models, fixture_folder, status_codes
):
    endpoint = mocked_management_instance['management_api_url'] + '/models'
    full_path = get_fixture_path(os.path.join('management', 'pagination', fixture_folder))
    files = sorted(os.listdir(full_path))
    expected_params = []
    params = {'limit': 100}
    for index, status_code in enumerate(status_codes):
        with open(os.path.join(full_path, files[index])) as f:
            payload = json.load(f)
        expected_params.append(params)
        fake_http_response(
            endpoint,
            json_data=payload,
            status_code=status_code,
            match_options={'params': params},
        )
        params = {'limit': 100, 'nextPageToken': payload.get('nextPageToken')}

    discovery = ModelDiscovery(check(mocked_management_instance), include=['.*'])
    assert [('.*', model['modelName'], model, None) for model in expected_models] == list(discovery.get_items())
    assert discovery.api_status == (AgentCheck.CRITICAL if status_codes[0] != 200 else AgentCheck.OK)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url, dict(r.options)) for r in fake_http.requests] == [
        ('GET', endpoint, {'params': params}) for params in expected_params
    ]
