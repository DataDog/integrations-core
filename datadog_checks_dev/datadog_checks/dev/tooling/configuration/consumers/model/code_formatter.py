# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shlex
import subprocess
import sys
from pathlib import Path

from datadog_checks.dev.tooling.constants import get_root


def format_with_ruff(source: str) -> str:
    """Format Python source via ``ruff format -`` (stdin/stdout).

    Replaces the line-wrapping role previously played by black on auto-generated
    config_models files. Uses the repo's centralized ruff configuration so the
    output matches the rest of the codebase. Invokes ruff through the active
    interpreter (``python -m ruff``) so the package installed alongside
    ``datadog_checks_dev[cli]`` is always picked up, regardless of PATH.
    """
    args = [sys.executable, '-m', 'ruff', 'format', '--quiet', '--stdin-filename=model.py']
    config_path = _resolve_ruff_config()
    if config_path is not None:
        args.extend(['--config', str(config_path)])
    else:
        args.extend(['--isolated', '--config', "format.quote-style='preserve'", '--line-length=120'])
    args.append('-')

    try:
        result = subprocess.run(
            args,
            input=source,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        # `python -m ruff` exits non-zero when the ruff package is missing,
        # surfacing as ModuleNotFoundError on stderr. Promote that to a
        # clearer install hint; otherwise propagate the underlying error
        # with enough context to reproduce the failure manually.
        stderr = e.stderr or ''
        if "No module named 'ruff'" in stderr:
            raise RuntimeError(
                "Cannot format auto-generated config models: the `ruff` package is not installed in the active "
                "interpreter. Reinstall `datadog_checks_dev[cli]` (or run `pip install ruff`) and retry."
            ) from e
        details = [f'{shlex.join(args)} failed', f'stderr: {stderr.strip()}']
        if e.stdout:
            details.append(f'stdout: {e.stdout.strip()}')
        raise RuntimeError(
            '`ruff format` failed while formatting auto-generated config models. ' + '; '.join(details)
        ) from e
    return result.stdout


def _resolve_ruff_config() -> Path | None:
    """Locate the repo pyproject.toml that holds the central ruff configuration.

    Prefer the path reported by ``get_root`` (set by ddev commands). Fall back
    to walking up from this module so unit tests, which never call ``set_root``,
    still pick up the same configuration as model regeneration.
    """
    root_str = get_root()
    if root_str:
        root = Path(root_str)
        if root.is_dir():
            candidate = root / 'pyproject.toml'
            if _has_ruff_section(candidate):
                return candidate

    for parent in Path(__file__).resolve().parents:
        candidate = parent / 'pyproject.toml'
        if _has_ruff_section(candidate):
            return candidate
    return None


def _has_ruff_section(pyproject: Path) -> bool:
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text()
    except OSError:
        return False
    return any(
        stripped == '[tool.ruff]' or stripped.startswith('[tool.ruff.')
        for stripped in (line.strip() for line in text.splitlines())
    )
