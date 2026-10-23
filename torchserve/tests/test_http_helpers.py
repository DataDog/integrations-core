# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import torchserve_api
from .common import INFERENCE_API_URL, MANAGEMENT_API_URL

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'function,args,method,endpoint,options,status',
    [
        (
            torchserve_api.run_prediction,
            ('model',),
            'POST',
            f'{INFERENCE_API_URL}/predictions/model',
            {'data': '{"input": 2.0}', 'headers': {'Content-Type': 'application/json'}},
            200,
        ),
        (
            torchserve_api.set_model_default_version,
            ('model', 2),
            'PUT',
            f'{MANAGEMENT_API_URL}/models/model/2/set-default',
            {},
            200,
        ),
        (
            torchserve_api.update_workers,
            ('model', 1, 3),
            'PUT',
            f'{MANAGEMENT_API_URL}/models/model',
            {'params': {'min_worker': 1, 'max_worker': 3}},
            202,
        ),
        (
            torchserve_api.register_model,
            ('model.mar',),
            'POST',
            f'{MANAGEMENT_API_URL}/models',
            {'params': {'url': 'model.mar'}},
            200,
        ),
    ],
)
@pytest.mark.parametrize('available', [True, False])
def test_environment_readiness(
    mocker, fake_http, fake_http_response, function, args, method, endpoint, options, status, available
):
    mocker.patch.object(torchserve_api, 'create_http_client', return_value=fake_http)
    fake_http_response(endpoint, method=method, status_code=status if available else 500)
    assert function(*args) is available
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url, dict(r.options)) for r in fake_http.requests] == [(method, endpoint, options)]
