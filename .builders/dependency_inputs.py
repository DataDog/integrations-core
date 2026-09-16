"""Shared path rules for dependency resolution inputs and outputs."""

from __future__ import annotations

SHARED_INPUTS = [
    'build.py',
    'deps/build_dependencies.txt',
    'scripts/**/*',
    'patches/**/*',
    'images/helpers.ps1',
    'images/install-from-source.sh',
    'images/runner_dependencies.txt',
]

ROOT_RESOLUTION_INPUTS = (
    'agent_requirements.in',
    '.github/workflows/resolve-build-deps.yaml',
)

RESOLUTION_INPUTS = [
    *ROOT_RESOLUTION_INPUTS,
    '.builders/build.py',
    '.builders/upload.py',
    '.builders/inputs_hash.py',
    '.builders/dependency_inputs.py',
    '.builders/targets.json',
    '.builders/deps/*.txt',
    '.builders/scripts/**/*',
    '.builders/patches/**/*',
    '.builders/images/**/*',
]

IGNORED_DIRS = (
    'tests/',
    'venv/',
)

IGNORED_FILES = frozenset({
    'dependency_wheel_promotion_gate.py',
    'promote.py',
    'pyproject.toml',
    'test_dependencies.txt',
    'AGENTS.md',
    'CLAUDE.md',
})


def _has_filtered_part(name: str, prefix: str) -> bool:
    return any(part.startswith('.') or part == '__pycache__' for part in name[len(prefix):].split('/'))


def affects_resolution(name: str) -> bool:
    """Whether changing a repository-relative path can affect dependency resolution."""
    if name in ROOT_RESOLUTION_INPUTS:
        return True
    prefix = '.builders/'
    if not name.startswith(prefix) or _has_filtered_part(name, prefix):
        return False
    relative = name[len(prefix):]
    if relative in IGNORED_FILES or any(relative.startswith(ignored) for ignored in IGNORED_DIRS):
        return False
    return True


def is_resolution_output(name: str) -> bool:
    """Whether a repository-relative path is published by dependency resolution."""
    prefix = '.deps/'
    return name.startswith(prefix) and not _has_filtered_part(name, prefix)
