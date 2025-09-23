# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from .common import INFERENCE_API_URL, MANAGEMENT_API_URL

# This file contains utility functions to interact with TorchServe API.
# They are mainly used to set up the e2e environment


def run_prediction(model):
    try:
        response = requests.post(
            f"{INFERENCE_API_URL}/predictions/{model}",
            data='{"input": 2.0}',
            headers={'Content-Type': 'application/json'},
        )
        response.raise_for_status()
    except Exception:
        return False
    else:
        return response.status_code == 200


def set_model_default_version(model, version):
    try:
        response = requests.put(
            f"{MANAGEMENT_API_URL}/models/{model}/{version}/set-default",
        )
        response.raise_for_status()
    except Exception:
        return False
    else:
        return response.status_code == 200


def update_workers(model, min, max):
    try:
        response = requests.put(
            f"{MANAGEMENT_API_URL}/models/{model}",
            params={
                "min_worker": min,
                "max_worker": max,
            },
        )
        response.raise_for_status()
    except Exception:
        return False
    else:
        return response.status_code == 202


def register_model(model):
    try:
        response = requests.post(f"{MANAGEMENT_API_URL}/models", params={"url": model})
        response.raise_for_status()
    except Exception:
        return False
    else:
        return response.status_code == 200
