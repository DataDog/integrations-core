# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.dev.utils import get_metadata_metrics

from . import common

# Use Caddy for testing due to the CUDA limitation preventing the spin of a Triton docker container.
# https://docs.nvidia.com/deeplearning/triton-inference-server/archives/triton_inference_server_1150/user-guide/docs/build.html#cuda-cublas-cudnn


def test_check_nvidia_triton(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    metrics = common.METRICS_MOCK

    for metric in metrics:
        aggregator.assert_metric(name=metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
