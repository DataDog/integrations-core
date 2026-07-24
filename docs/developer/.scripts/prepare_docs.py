"""Pre-build step that materializes the developer docs into a staging directory.

Zensical does not run MkDocs hooks or the `mkpatcher` extension, so this script
applies the same substitutions ahead of the build:

- Replaces `<docs-insert-ddev-version>` markers with the current ddev version.
- Replaces `<docs-insert-status>` in `meta/status.md` with the integrations
  status tables rendered by `33_render_status.py`.
- Replaces `<docs-insert-dependencies>` in `faq/acknowledgements.md` with the
  bundled dependency list rendered by `66_render_dependencies.py`.

The original sources under `docs/developer/` are left untouched; the patched
copy is written to `docs/developer-build/` (the `docs_dir` configured in
`mkdocs.yml`).
"""

import os
import shutil
import subprocess
import sys
from functools import cache
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent
TARGET_DIR = SOURCE_DIR.parent / 'developer-build'

EXCLUDED_TOP_LEVEL = {'.scripts', '.hooks'}

VERSION_MARKER = '<docs-insert-ddev-version>'
STATUS_MARKER = '<docs-insert-status>'
DEPENDENCIES_MARKER = '<docs-insert-dependencies>'

SEMVER_PARTS = 3


@cache
def get_latest_ddev_version() -> str:
    repo_root = SOURCE_DIR.parents[1]
    ddev_root = repo_root / 'ddev'
    env = os.environ.copy()
    env.pop('HATCH_ENV_ACTIVE', None)
    output = subprocess.check_output(['hatch', 'version'], cwd=str(ddev_root), env=env).decode('utf-8').strip()

    version = output.replace('dev', '')
    parts = list(map(int, version.split('.')))
    major, minor, patch = parts[:SEMVER_PARTS]
    if len(parts) > SEMVER_PARTS:
        patch -= 1
    return f'{major}.{minor}.{patch}'


def _import_renderers():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import importlib

        status = importlib.import_module('33_render_status')
        deps = importlib.import_module('66_render_dependencies')
        root_setter = importlib.import_module('00_set_root')
    finally:
        sys.path.pop(0)
    return status.patch, deps.patch, root_setter.patch


def _apply_lines_patch(path: Path, marker: str, patcher) -> None:
    text = path.read_text(encoding='utf-8')
    if marker not in text:
        return
    lines = text.splitlines()
    patched = patcher(lines)
    if patched is None:
        return
    path.write_text('\n'.join(patched) + '\n', encoding='utf-8')


def _apply_version_substitutions(target: Path) -> None:
    version = get_latest_ddev_version()
    for md in target.rglob('*.md'):
        text = md.read_text(encoding='utf-8')
        if VERSION_MARKER not in text:
            continue
        md.write_text(text.replace(VERSION_MARKER, version), encoding='utf-8')


def _ignore(_: str, names: list[str]) -> set[str]:
    return {n for n in names if n in EXCLUDED_TOP_LEVEL or n == '__pycache__'}


def main() -> None:
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    shutil.copytree(SOURCE_DIR, TARGET_DIR, ignore=_ignore)

    status_patch, deps_patch, set_root_patch = _import_renderers()
    set_root_patch([])

    _apply_lines_patch(TARGET_DIR / 'meta' / 'status.md', STATUS_MARKER, status_patch)
    _apply_lines_patch(TARGET_DIR / 'faq' / 'acknowledgements.md', DEPENDENCIES_MARKER, deps_patch)
    _apply_version_substitutions(TARGET_DIR)


if __name__ == '__main__':
    main()
