# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.stop_flow import StopFlowInput, StopFlowTool


async def test_call_reports_stop_reason_from_input() -> None:
    result = await StopFlowTool()(StopFlowInput(reason="the PRD endpoint doesn't exist"))

    assert result.success is True
    assert result.stop_reason == "the PRD endpoint doesn't exist"
