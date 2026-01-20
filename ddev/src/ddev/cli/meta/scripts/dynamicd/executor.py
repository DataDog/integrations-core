# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Script execution with error handling and retries for DynamicD."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ddev.cli.meta.scripts.dynamicd.constants import (
    DOCKER_CPU_LIMIT,
    DOCKER_IMAGE,
    DOCKER_MEMORY_LIMIT,
    FAKE_DATA_DIR,
    MAX_RETRIES,
)
from ddev.cli.meta.scripts.dynamicd.generator import GeneratorError, fix_script_error


@dataclass
class ExecutionResult:
    """Result of script execution."""

    success: bool
    return_code: int
    stdout: str
    stderr: str
    script: str
    attempts: int


class ExecutionError(Exception):
    """Error during script execution."""


def is_docker_available() -> bool:
    """Check if Docker is installed and the daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def execute_script(
    script: str,
    dd_api_key: str,
    llm_api_key: str,
    timeout: int | None = None,
    on_status: Callable[[str], None] | None = None,
    sandbox: bool = False,
) -> ExecutionResult:
    """
    Execute the generated script with automatic error correction.

    Args:
        script: The Python script to execute
        dd_api_key: Datadog API key to inject
        llm_api_key: Anthropic API key for error correction
        timeout: Execution timeout in seconds (None = no timeout)
        on_status: Optional callback for status updates
        sandbox: If True, run script in Docker container for isolation

    Returns:
        ExecutionResult with success status and output
    """

    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    current_script = script
    attempt = 0
    result: _RunResult | None = None

    # Pass API key as environment variable (most reliable method)
    env_vars = {"DATADOG_API_KEY": dd_api_key}

    # Select execution method
    if sandbox:
        run_func = _run_script_in_container
        status("Running in Docker sandbox...")
    else:
        run_func = _run_script

    while attempt < MAX_RETRIES:
        attempt += 1
        status(f"Executing script (attempt {attempt}/{MAX_RETRIES})...")

        # Inject the Datadog API key into the script as well (belt and suspenders)
        executable_script = _inject_api_key(current_script, dd_api_key)

        # Write to temp file and execute with env var
        # Use lambda to ensure flush=True for real-time output
        result = run_func(executable_script, timeout, env_vars=env_vars, on_output=lambda x: print(x, flush=True))

        if result.return_code == 0:
            status("Script executed successfully!")
            return ExecutionResult(
                success=True,
                return_code=result.return_code,
                stdout=result.stdout,
                stderr=result.stderr,
                script=current_script,
                attempts=attempt,
            )

        # Script failed - try to fix it
        error_message = f"Exit code: {result.return_code}\n"
        if result.stderr:
            error_message += f"Stderr:\n{result.stderr}\n"
        if result.stdout:
            error_message += f"Stdout:\n{result.stdout}\n"

        status(f"Script failed:\n{error_message[:500]}")

        if attempt < MAX_RETRIES:
            try:
                current_script = fix_script_error(
                    original_script=current_script,
                    error_message=error_message,
                    attempt=attempt,
                    api_key=llm_api_key,
                    on_status=on_status,
                )
            except GeneratorError as e:
                status(f"Could not get error fix from LLM: {e}")
                break
        else:
            status(f"Max retries ({MAX_RETRIES}) exceeded")

    # All retries exhausted or MAX_RETRIES is 0
    if result is None:
        return ExecutionResult(
            success=False,
            return_code=-1,
            stdout="",
            stderr="No execution attempts made (MAX_RETRIES=0)",
            script=current_script,
            attempts=0,
        )

    return ExecutionResult(
        success=False,
        return_code=result.return_code,
        stdout=result.stdout,
        stderr=result.stderr,
        script=current_script,
        attempts=attempt,
    )


def validate_script_syntax(script: str) -> tuple[bool, str]:
    """
    Validate Python script syntax without executing.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(script, "<script>", "exec")
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


def save_script(
    script: str,
    integration_path: Path,
    integration_name: str,
    scenario: str,
) -> Path:
    """
    Save the generated script to the integration's fake_data directory.

    Args:
        script: The Python script to save
        integration_path: Path to the integration directory
        integration_name: Name of the integration
        scenario: The scenario used

    Returns:
        Path to the saved script
    """
    fake_data_dir = integration_path / FAKE_DATA_DIR
    fake_data_dir.mkdir(exist_ok=True)

    # Create filename based on integration and scenario
    filename = f"{integration_name}_sim_{scenario}.py"
    script_path = fake_data_dir / filename

    # Add header comment
    header = f'''# Generated by DynamicD
# Integration: {integration_name}
# Scenario: {scenario}
#
# Usage:
#   export DATADOG_API_KEY="your-api-key"
#   python {filename}
#
# To modify scenarios, change the SCENARIO variable at the top of the script.

'''
    full_script = header + script

    script_path.write_text(full_script, encoding="utf-8")

    return script_path


@dataclass
class _RunResult:
    """Internal result from running a script."""

    return_code: int
    stdout: str
    stderr: str


def _run_script(
    script: str,
    timeout: int | None,
    env_vars: dict[str, str] | None = None,
    on_output: Callable[[str], None] | None = None,
) -> _RunResult:
    """Run a script in a subprocess with real-time output streaming."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(script)
        temp_path = f.name

    # Merge environment variables
    run_env = {**os.environ}
    if env_vars:
        run_env.update(env_vars)

    try:
        # Stream output in real-time
        process = subprocess.Popen(
            [sys.executable, "-u", temp_path],  # -u for unbuffered output
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=run_env,
            bufsize=1,  # Line buffered
        )

        stdout_lines: list[str] = []
        try:
            if process.stdout is None:
                raise ExecutionError("Failed to capture stdout from subprocess")
            for line in process.stdout:
                if on_output:
                    on_output(line.rstrip('\n'))  # Stream output via callback
                stdout_lines.append(line)
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            return _RunResult(
                return_code=-1,
                stdout=''.join(stdout_lines),
                stderr=f"Script timed out after {timeout} seconds",
            )

        return _RunResult(
            return_code=process.returncode,
            stdout=''.join(stdout_lines),
            stderr='',
        )
    except Exception as e:
        return _RunResult(
            return_code=-1,
            stdout="",
            stderr=str(e),
        )
    finally:
        try:
            Path(temp_path).unlink()
        except OSError:
            pass


def _run_script_in_container(
    script: str,
    timeout: int | None,
    env_vars: dict[str, str] | None = None,
    on_output: Callable[[str], None] | None = None,
) -> _RunResult:
    """Run a script in a Docker container with real-time output streaming."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(script)
        temp_path = f.name

    try:
        # Build docker run command
        docker_cmd = [
            "docker",
            "run",
            "--rm",  # Auto-remove container when done
            "--network",
            "host",  # Allow network access for Datadog API
            "--memory",
            DOCKER_MEMORY_LIMIT,
            "--cpus",
            DOCKER_CPU_LIMIT,
            "-v",
            f"{temp_path}:/script.py:ro",  # Mount script read-only
        ]

        # Add environment variables
        if env_vars:
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

        # Add image and command - install dependencies via shell then run script
        docker_cmd.extend(
            [
                DOCKER_IMAGE,
                "sh",
                "-c",
                "pip install -q requests && python -u /script.py",
            ]
        )

        # Stream output in real-time
        process = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
        )

        stdout_lines: list[str] = []
        try:
            if process.stdout is None:
                raise ExecutionError("Failed to capture stdout from subprocess")
            for line in process.stdout:
                if on_output:
                    on_output(line.rstrip('\n'))  # Stream output via callback
                stdout_lines.append(line)
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            # Also try to stop any running container
            subprocess.run(["docker", "kill", "--signal=SIGKILL"], capture_output=True)
            return _RunResult(
                return_code=-1,
                stdout=''.join(stdout_lines),
                stderr=f"Script timed out after {timeout} seconds",
            )

        return _RunResult(
            return_code=process.returncode,
            stdout=''.join(stdout_lines),
            stderr='',
        )
    except Exception as e:
        return _RunResult(
            return_code=-1,
            stdout="",
            stderr=str(e),
        )
    finally:
        try:
            Path(temp_path).unlink()
        except OSError:
            pass


def _inject_api_key(script: str, api_key: str) -> str:
    """Inject the Datadog API key into the script.

    Replaces the placeholder API key with the actual key. The API key is also
    passed via environment variable as a fallback (see execute_script).
    """
    # Use json.dumps for robust escaping of all special characters
    safe_api_key = json.dumps(api_key)  # Returns quoted string like '"key"'

    # Replace placeholder with actual key
    script = script.replace('DATADOG_API_KEY = "YOUR_API_KEY"', f'DATADOG_API_KEY = {safe_api_key}')

    return script
