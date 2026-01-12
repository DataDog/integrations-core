# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Claude API interaction for DynamicD."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ddev.cli.meta.scripts.dynamicd.constants import DEFAULT_MODEL, MAX_TOKENS
from ddev.cli.meta.scripts.dynamicd.prompts import (
    build_error_correction_prompt,
    build_stage1_prompt,
    build_stage2_prompt,
)

if TYPE_CHECKING:
    from ddev.cli.meta.scripts.dynamicd.context_builder import IntegrationContext


class GeneratorError(Exception):
    """Error during script generation."""


def generate_simulator_script(
    context: IntegrationContext,
    scenario: str,
    dd_site: str,
    metrics_per_second: int,
    duration: int,
    api_key: str,
    model: str = DEFAULT_MODEL,
    on_status: callable | None = None,
) -> str:
    """
    Generate a simulator script using two-stage LLM prompting.

    Args:
        context: Integration context with metadata
        scenario: Selected scenario (healthy, degraded, etc.)
        dd_site: Datadog site URL
        metrics_per_second: Target metrics rate
        duration: Duration in seconds (0 = forever)
        api_key: Anthropic API key
        model: Claude model to use
        on_status: Optional callback for status updates

    Returns:
        Generated Python script as a string
    """
    try:
        import anthropic
    except ImportError as e:
        raise GeneratorError(
            "anthropic package is required. Install with: pip install anthropic"
        ) from e

    client = anthropic.Anthropic(api_key=api_key)

    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    # Stage 1: Analyze the integration
    status("Stage 1: Analyzing integration context...")
    integration_context_str = context.to_prompt_context()

    stage1_system, stage1_user = build_stage1_prompt(
        integration_context=integration_context_str,
        display_name=context.display_name,
    )

    try:
        # Use streaming for long-running operations (required for Opus)
        stage1_analysis = ""
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            temperature=0,  # Deterministic output
            system=stage1_system,
            messages=[{"role": "user", "content": stage1_user}],
        ) as stream:
            for text in stream.text_stream:
                stage1_analysis += text
    except anthropic.APIError as e:
        raise GeneratorError(f"Stage 1 API error: {e}") from e

    status("Stage 1 complete: Service analysis ready")

    # Stage 2: Generate the script
    status(f"Stage 2: Generating simulator script for scenario '{scenario}'...")

    stage2_system, stage2_user = build_stage2_prompt(
        integration_context=integration_context_str,
        display_name=context.display_name,
        stage1_analysis=stage1_analysis,
        scenario=scenario,
        dd_site=dd_site,
        metrics_per_second=metrics_per_second,
        duration=duration,
    )

    try:
        # Use streaming for long-running operations (required for Opus)
        script = ""
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            temperature=0,  # Deterministic output
            system=stage2_system,
            messages=[{"role": "user", "content": stage2_user}],
        ) as stream:
            for text in stream.text_stream:
                script += text
    except anthropic.APIError as e:
        raise GeneratorError(f"Stage 2 API error: {e}") from e

    # Clean up the script (remove markdown code blocks if present)
    script = _clean_script(script)

    status("Stage 2 complete: Script generated")

    return script


def fix_script_error(
    original_script: str,
    error_message: str,
    attempt: int,
    api_key: str,
    model: str = DEFAULT_MODEL,
    on_status: callable | None = None,
) -> str:
    """
    Use the LLM to fix an error in the generated script.

    Args:
        original_script: The script that had an error
        error_message: The error message
        attempt: Current attempt number
        api_key: Anthropic API key
        model: Claude model to use
        on_status: Optional callback for status updates

    Returns:
        Corrected Python script as a string
    """
    try:
        import anthropic
    except ImportError as e:
        raise GeneratorError(
            "anthropic package is required. Install with: pip install anthropic"
        ) from e

    client = anthropic.Anthropic(api_key=api_key)

    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    status(f"Attempt {attempt}: Asking LLM to fix the error...")

    system_prompt, user_prompt = build_error_correction_prompt(
        original_script=original_script,
        error_message=error_message,
        attempt=attempt,
    )

    try:
        # Use streaming for long-running operations (required for Opus)
        fixed_script = ""
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            temperature=0,  # Deterministic output
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                fixed_script += text
    except anthropic.APIError as e:
        raise GeneratorError(f"Error correction API error: {e}") from e

    # Clean up the script
    fixed_script = _clean_script(fixed_script)

    status("Received corrected script")

    return fixed_script


def _clean_script(script: str) -> str:
    """Remove markdown code blocks and clean up the script."""
    script = script.strip()

    # Remove markdown code blocks
    if script.startswith("```python"):
        script = script[9:]
    elif script.startswith("```"):
        script = script[3:]

    if script.endswith("```"):
        script = script[:-3]

    script = script.strip()

    # Ensure it starts with a shebang or docstring
    if not script.startswith("#") and not script.startswith('"""') and not script.startswith("'''"):
        script = "#!/usr/bin/env python3\n" + script

    return script

