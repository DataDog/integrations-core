# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Guard against erosion of the OS wrapper seam.

Two regressions are cheap to introduce and invisible in tests:

1. A raw ``open()``/``subprocess`` call reintroduces unmediated I/O, so a
   config-derived path bypasses validation entirely.
2. A check module reaches for the module-level ``unchecked_os`` singleton, which
   is permanently bound to the no-op validator. That passes every existing test
   while enforcing nothing, which is worse than an obvious bypass because it
   looks like coverage.

Both are legitimate in narrow cases, so an inline ``# SKIP_OS_WRAPPER_VALIDATION``
waiver is honored on the offending line or in the comment block above it, forcing
the decision to be written down. A waiver in a file header waives the whole file.

Detection is AST-based: a method named ``open``, or the word in a docstring, is
not a call and must not be reported.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

WAIVER = 'SKIP_OS_WRAPPER_VALIDATION'

# Dotted stdlib call targets that must go through the interface instead.
MEDIATED_CALLS = frozenset(
    {
        'subprocess.run',
        'subprocess.Popen',
        'subprocess.call',
        'subprocess.check_output',
        'subprocess.check_call',
        'os.open',
        'os.listdir',
        'os.scandir',
        'os.walk',
        'os.remove',
        'os.unlink',
        'os.rename',
        'os.system',
        'os.path.exists',
        'os.path.isfile',
        'os.path.isdir',
        'os.path.islink',
        'os.path.getsize',
        'os.path.realpath',
        'glob.glob',
        'shutil.copy',
        'shutil.which',
    }
)

CHECK_BASE_NAMES = frozenset({'AgentCheck', 'OpenMetricsBaseCheck', 'OpenMetricsBaseCheckV2'})

# `from os import scandir` binds a bare name that dotted matching cannot see, so
# these imports are tracked and their local names resolved back to dotted form.
MEDIATED_MEMBERS = {
    'os': {'listdir', 'scandir', 'walk', 'remove', 'unlink', 'rename', 'system', 'open'},
    'os.path': {'exists', 'isfile', 'isdir', 'islink', 'getsize', 'realpath'},
    'subprocess': {'run', 'Popen', 'call', 'check_output', 'check_call'},
    'shutil': {'copy', 'which'},
    'glob': {'glob'},
}


def _imported_aliases(tree: ast.Module) -> dict[str, str]:
    """Map locally bound names to the dotted mediated call they refer to."""
    aliases = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module not in MEDIATED_MEMBERS:
            continue
        members = MEDIATED_MEMBERS[node.module]
        for imported in node.names:
            if imported.name in members:
                aliases[imported.asname or imported.name] = f'{node.module}.{imported.name}'
    return aliases


def _dotted_name(node: ast.AST) -> str | None:
    """Render an attribute/name chain such as `os.path.exists` as a string."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return '.'.join(reversed(parts))


def _defines_check_class(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            name = _dotted_name(base)
            if name and name.split('.')[-1] in CHECK_BASE_NAMES:
                return True
    return False


def validate_file(path: str) -> list[str]:
    """Return one message per unwaived violation in `path`."""
    with open(path, encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    # A waiver in the file header waives the whole file (used for vendored code).
    if any(WAIVER in line for line in lines[:5]):
        return []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Vendored py2 sources and the like; other tooling covers syntax.
        return []

    def waived(lineno: int) -> bool:
        """True when the call carries a waiver, inline or in the comment block above it.

        The whole contiguous run of comment lines directly above the call is
        considered, since a justification usually needs more than one line. A
        blank line breaks the association, so a waiver cannot apply to a call it
        is merely near.
        """
        index = lineno - 1
        if index >= len(lines):
            return False
        if WAIVER in lines[index]:
            return True
        cursor = index - 1
        while cursor >= 0 and lines[cursor].lstrip().startswith('#'):
            if WAIVER in lines[cursor]:
                return True
            cursor -= 1
        return False

    errors = []
    check_module = _defines_check_class(tree)
    aliases = _imported_aliases(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        target = node.func
        if isinstance(target, ast.Name) and target.id == 'open' and 'open' not in aliases:
            if not waived(node.lineno):
                errors.append(
                    f'{path}:{node.lineno}: uses `open(` directly; route it through '
                    f'`self.os.open` so config-derived paths are validated. If the path '
                    f'cannot come from config, add an inline `# {WAIVER}` comment.'
                )
            continue

        # A bare name bound by `from os import scandir` refers to the same call.
        if isinstance(target, ast.Name) and target.id in aliases:
            if not waived(node.lineno):
                errors.append(
                    f'{path}:{node.lineno}: uses `{aliases[target.id]}` directly (imported as '
                    f'`{target.id}`); route it through `self.os` so config-derived paths are '
                    f'validated. If the path cannot come from config, add an inline `# {WAIVER}` comment.'
                )
            continue

        dotted = _dotted_name(target)
        if dotted is None:
            continue

        if dotted in MEDIATED_CALLS and not waived(node.lineno):
            errors.append(
                f'{path}:{node.lineno}: uses `{dotted}` directly; route it through '
                f'`self.os` so config-derived paths are validated. If the path cannot '
                f'come from config, add an inline `# {WAIVER}` comment.'
            )
        elif check_module and dotted.startswith('unchecked_os.') and not waived(node.lineno):
            errors.append(
                f'{path}:{node.lineno}: uses the module-level `unchecked_os` singleton in a check '
                f'module. That singleton is bound to the no-op validator and can never enforce '
                f'anything. Use `self.os`, or pass it into module-level helpers. If this '
                f'path cannot come from config, add an inline `# {WAIVER}` comment.'
            )

    return errors


@click.command(short_help='Validate OS wrapper usage')
@click.argument('integrations', nargs=-1)
@click.pass_obj
def os_wrapper(app: Application, integrations: tuple[str, ...]):
    """Validate that integrations reach the filesystem and subprocesses through
    the OS wrapper rather than raw stdlib calls or the unenforcing
    module-level singleton.

    If `integrations` is specified, only those will be validated; 'all' validates
    every integration.
    """
    validation_tracker = app.create_validation_tracker('OS wrapper validation')

    excluded = set(app.repo.config.get('/overrides/validate/os-wrapper/exclude', []))
    for integration in app.repo.integrations.iter(integrations):
        if integration.name in excluded or not integration.is_integration:
            continue

        errors: list[str] = []
        for file in integration.package_files():
            file_str = str(file)
            # config_models are generated from spec.yaml and are not hand-edited.
            if not file_str.endswith('.py') or 'config_models' in file_str:
                continue
            errors.extend(validate_file(file_str))

        if errors:
            validation_tracker.error((integration.display_name,), message='\n'.join(errors))
        else:
            validation_tracker.success()

    validation_tracker.display()
    if validation_tracker.errors:
        app.abort()
