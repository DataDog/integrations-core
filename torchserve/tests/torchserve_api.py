# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .common import INFERENCE_API_URL, MANAGEMENT_API_URL

# This file contains utility functions to interact with TorchServe API.
# They are mainly used to set up the e2e environment


def with_query_params(url: str, params: dict[str, object]) -> str:
    return '{}?{}'.format(url, urlencode(params))


def send_request(http_request: Request) -> int:
    with urlopen(http_request) as response:
        return response.status


def run_prediction(model):
    try:
        status = send_request(
            Request(
                f"{INFERENCE_API_URL}/predictions/{model}",
                data=b'{"input": 2.0}',
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
        )
    except Exception:
        return False
    else:
        return status == 200


def set_model_default_version(model, version):
    try:
        status = send_request(
            Request(
                f"{MANAGEMENT_API_URL}/models/{model}/{version}/set-default",
                method='PUT',
            )
        )
    except Exception:
        return False
    else:
        return status == 200


def update_workers(model, min, max):
    try:
        status = send_request(
            Request(
                with_query_params(
                    f"{MANAGEMENT_API_URL}/models/{model}",
                    {
                        "min_worker": min,
                        "max_worker": max,
                    },
                ),
                method='PUT',
            )
        )
    except Exception:
        return False
    else:
        return status == 202


def register_model(model):
    try:
        status = send_request(Request(with_query_params(f"{MANAGEMENT_API_URL}/models", {"url": model}), method='POST'))
    except Exception:
        return False
    else:
        return status == 200
