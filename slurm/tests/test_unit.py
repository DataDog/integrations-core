# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.slurm import SlurmCheck
from unittest.mock import patch

from .common import SLURM_VERSION, mock_output


# def test_check(dd_run_check, aggregator, instance):
#     # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
#     check = SlurmCheck('slurm', {}, [instance])
#     dd_run_check(check)

#     aggregator.assert_all_metrics_covered()
#     aggregator.assert_metrics_using_metadata(get_metadata_metrics())

@patch('datadog_checks.slurm.check.get_subprocess_out')
def test_metadata(mock_get_subprocess_out, instance, datadog_agent, dd_run_check):
    instance['collect_sinfo_stats'] = True
    instance['sinfo_collection_level'] = 1
    check = SlurmCheck('slurm', {}, [instance])
    check.check_id = 'test:123'

    mock_sinfo_output = mock_output('sinfo_version.txt')
    
    # First return for the metadata, the second one is for the sinfo partition
    # metric collection. But we don't care about that here.
    mock_get_subprocess_out.side_effect = [
        (mock_sinfo_output, "", 0),
        ("", "", 1),
    ]

    dd_run_check(check)

    raw_version = SLURM_VERSION
    major, minor, mod = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'slurm',
        'version.major': major,
        'version.minor': minor,
        'version.mod': mod,
        'version.raw': raw_version,
    }
    datadog_agent.assert_metadata('test:123', version_metadata)