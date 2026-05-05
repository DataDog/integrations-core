# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil
import subprocess
from pathlib import Path

from datadog_checks.dev.tooling.constants import get_root


def format_with_ruff(source: str) -> str:
    """Format Python source via `ruff format -` (stdin/stdout).

    Replaces the line-wrapping role previously played by black on auto-generated
    config_models files. Uses the repo's centralized ruff configuration so the
    output matches the rest of the codebase. Returns the input unchanged if
    ruff is unavailable, so unrelated tooling is not broken.
    """
    ruff = shutil.which('ruff')
    if ruff is None:
        return source

    args = [ruff, 'format', '--quiet', '--stdin-filename=model.py']
    config_path = _resolve_ruff_config()
    if config_path is not None:
        args.extend(['--config', str(config_path)])
    else:
        args.extend(['--isolated', '--config', "format.quote-style='preserve'", '--line-length=120'])
    args.append('-')

    result = subprocess.run(
        args,
        input=source,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return source
    return result.stdout


def _resolve_ruff_config() -> Path | None:
    """Locate the repo pyproject.toml that holds the central ruff configuration.

    Prefer the path reported by ``get_root`` (set by ddev commands). Fall back
    to walking up from this module so unit tests, which never call ``set_root``,
    still pick up the same configuration as model regeneration.
    """
    root = Path(get_root())
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
        return '[tool.ruff' in pyproject.read_text()
    except OSError:
        return False
