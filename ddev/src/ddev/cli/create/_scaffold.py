# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Template rendering for `ddev create` subcommands.

This module is loaded lazily from the subcommand functions (not at the
group / module top-level) so that `ddev create --help` stays fast.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path as _StdPath
from typing import TYPE_CHECKING, Any, TypedDict, cast
from uuid import uuid4

from ddev.cli.create._naming import (
    get_config_models_documentation,
    get_license_header,
    kebab_case_name,
    normalize_package_name,
    normalize_project_name,
)
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ddev.cli.application import Application

TEMPLATES_ROOT = Path(_StdPath(__file__).parent / 'templates')

BINARY_EXTENSIONS = ('.png',)

CHECK_LINKS = """\
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/{repository}/blob/master/{name}/datadog_checks/{name}/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/{repository}/blob/master/{name}/metadata.csv
[8]: https://github.com/DataDog/{repository}/blob/master/{name}/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
"""

LOGS_LINKS = """\
[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[4]: **LINK_TO_INTEGRATION_SITE**
[5]: https://github.com/DataDog/{repository}/blob/master/{name}/assets/service_checks.json
"""

JMX_LINKS = """\
[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/{repository}/blob/master/{name}/datadog_checks/{name}/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/integrations/java/
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[8]: https://github.com/DataDog/{repository}/blob/master/{name}/assets/service_checks.json
"""

TILE_LINKS = """\
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
"""

EVENT_TILE_LINKS = """\
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://docs.datadoghq.com/help/
"""

INTEGRATION_TYPE_LINKS: dict[str, str] = {
    'check': CHECK_LINKS,
    'logs': LOGS_LINKS,
    'jmx': JMX_LINKS,
    'metrics_crawler': TILE_LINKS,
    'event': EVENT_TILE_LINKS,
}

TOWNCRIER_BODY = """\
<!-- towncrier release notes start -->
"""

PIPE = '│'
PIPE_MIDDLE = '├'
PIPE_END = '└'
HYPHEN = '──'


@dataclass
class TemplateFile:
    """A single rendered template file ready to be written to disk.

    Invariant on ``contents`` (mirrored by the ``# type: ignore`` lines in ``write()``):
      - ``binary=True``  => ``contents`` is ``bytes`` after ``read()``.
      - ``binary=False`` => ``contents`` is ``str``   after ``read()``.
      - ``contents`` is ``None`` only before ``read()`` has run.

    A discriminated union (one dataclass per branch) was considered but the
    structural overhead — two classes, two ``isinstance`` branches at every call
    site — outweighed the type-system clarity gain.
    """

    target_path: Path
    source_path: Path
    binary: bool
    contents: bytes | str | None = None

    def read(self, config: dict[str, Any]) -> None:
        if self.binary:
            self.contents = self.source_path.read_bytes()
            return
        raw = self.source_path.read_text()
        # Templates are trusted; a RuntimeError here indicates a broken shipped template, not user error.
        # User-supplied `name` is validated upstream by `is_valid_integration_name` before scaffolding starts.
        try:
            self.contents = raw.format(**config)
        except (KeyError, IndexError, ValueError) as exc:
            raise RuntimeError(f'Failed to render template {self.source_path}: {exc}') from exc

    def write(self) -> None:
        if self.contents is None:
            raise RuntimeError(f'read() must be called before write() (target: {self.target_path})')
        self.target_path.ensure_parent_dir_exists()
        if self.binary:
            self.target_path.write_bytes(self.contents)  # type: ignore[arg-type]
        else:
            self.target_path.write_text(self.contents)  # type: ignore[arg-type]


@dataclass
class ScaffoldResult:
    integration_dir: Path
    files: list[TemplateFile]
    config: dict[str, Any] = field(default_factory=dict)


class CheckOnlyPrefillFields(TypedDict, total=False):
    """Fields prefilled from a `check_only` integration's existing ``manifest.json``.

    All keys are optional: only the entries whose source field was present in the
    manifest are populated (legacy behaviour).
    """

    author_name: str
    check_name: str
    email: str
    homepage: str
    sales_email: str


def prefill_check_only_fields(
    manifest: dict[str, Any],
    normalized_name: str,
    author_normalized: str,
) -> CheckOnlyPrefillFields:
    """Extract reusable fields from a pre-existing `manifest.json` for a `check_only` integration.

    ``author_normalized`` is the already-validated, normalized author name resolved by the
    caller; we reuse it for the package name instead of re-deriving it from the raw manifest.
    """
    check_name = normalize_package_name(f'{author_normalized}_{normalized_name}')
    candidates: dict[str, str | None] = {
        'author_name': author_normalized,
        'check_name': check_name,
        'email': (manifest.get('author') or {}).get('support_email'),
        'homepage': (manifest.get('author') or {}).get('homepage'),
        'sales_email': (manifest.get('author') or {}).get('sales_email'),
    }
    return cast(CheckOnlyPrefillFields, {k: v for k, v in candidates.items() if v is not None})


def construct_template_fields(
    name: str,
    integration_type: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build the dict of substitution fields for the templates.

    The dropped types (`tile`, `snmp_tile`, `marketplace`) are intentionally
    not handled here: the revamp only exposes core-style subcommands.
    """
    normalized_name = normalize_package_name(name)
    check_name_kebab = kebab_case_name(name)

    if integration_type == 'check_only':
        check_name = ''
        author = ''
        email = ''
        email_packages = ''
        install_info = _third_party_install_info(name, normalized_name)
        license_header = ''
        support_type = ''
        integration_links = ''
    else:
        check_name = normalized_name
        author = 'Datadog'
        email = 'help@datadoghq.com'
        email_packages = 'packages@datadoghq.com'
        install_info = (
            f'The {name} check is included in the [Datadog Agent][2] package.\n'
            'No additional installation is needed on your server.'
        )
        license_header = get_license_header()
        support_type = 'core'
        integration_links_template = INTEGRATION_TYPE_LINKS.get(integration_type, '')
        integration_links = integration_links_template.format(
            name=normalized_name,
            repository='integrations-core',
        )

    config: dict[str, Any] = {
        'author': author,
        'auto_install': 'false' if integration_type == 'metrics_crawler' else 'true',
        'check_name': check_name,
        'project_name': normalize_project_name(normalized_name),
        'documentation': get_config_models_documentation(),
        'integration_name': name,
        'check_name_kebab': check_name_kebab,
        'email': email,
        'email_packages': email_packages,
        'app_uuid': uuid4(),
        'license_header': license_header,
        'install_info': install_info,
        'repo_choice': 'core',
        'repo_name': 'integrations-core',
        'support_type': support_type,
        'integration_links': integration_links,
        'source_type_id': int(datetime.now(timezone.utc).timestamp()) - 1_700_000_000,
        'manifest_version': '1.0.0',
        'today': date.today(),
        'changelog_body': TOWNCRIER_BODY,
        'starting_version': '0.0.1',
        'display_on_public_website': 'false',
        'media': '[]',
        'description': '<FILL IN - A brief description of what this offering provides>',
        'example_dashboard_short_name': '<FILL IN dashboard short_name ex: integration name overview>',
        'pricing_plan': '',
        'terms': '',
        'integration_id': kebab_case_name(name),
        'package_url': (
            "\n    # The project's main homepage.\n    url='https://github.com/DataDog/integrations-core',"
        ),
        'author_info': (
            '\n  "author": {\n'
            '    "support_email": "help@datadoghq.com",\n'
            '    "name": "Datadog",\n'
            '    "homepage": "https://www.datadoghq.com",\n'
            '    "sales_email": "info@datadoghq.com"\n'
            '  }'
        ),
    }
    config.update(kwargs)

    # Derive check_class from the final check_name: for check_only, prefilled fields
    # may supply a check_name that differs from normalized_name.
    package_name = config['check_name'] or normalized_name
    config['check_class'] = f"{''.join(part.capitalize() for part in package_name.split('_'))}Check"

    # An empty check_name would let template paths like '{check_name}/...' collapse to an
    # absolute '/...', discarding the target root and scaffolding to the filesystem root.
    # Upstream validation guarantees a non-empty name; assert it locally so a regression fails loudly.
    assert config['check_name'], 'check_name must be populated before scaffolding'
    return config


def _third_party_install_info(name: str, normalized_name: str) -> str:
    return (
        f'To install the {name} check on your host:\n\n\n'
        '1. Install the [developer toolkit]\n'
        '(https://docs.datadoghq.com/developers/integrations/python/)\n'
        ' on any machine.\n\n'
        f'2. Run `ddev release build {normalized_name}` to build the package.\n\n'
        '3. [Download the Datadog Agent][2].\n\n'
        '4. Upload the build artifact to any host with an Agent and\n'
        ' run `datadog-agent integration install -w\n'
        f' path/to/{normalized_name}/dist/<ARTIFACT_NAME>.whl`.'
    )


def collect_template_files(
    integration_type: str,
    target_root: Path,
    config: dict[str, Any],
    *,
    target_integration_dir: str,
    include_manifest: bool,
    read: bool,
) -> list[TemplateFile]:
    """Walk the template directory for `integration_type` and produce the file list.

    ``target_integration_dir`` is the on-disk directory name that should hold the
    rendered files. Template paths are formatted with ``config`` first; when the
    resulting top-level segment is the template ``{check_name}`` value we rewrite it
    to ``target_integration_dir`` so callers can keep the Python package name (which
    drives ``{check_name}``) distinct from the integration's directory name.
    """
    template_root = TEMPLATES_ROOT / integration_type
    if not template_root.is_dir():
        return []

    files: list[TemplateFile] = []
    template_check_name = config['check_name']
    for source in _walk_template(template_root):
        rel = source.relative_to(template_root)
        rel_str = str(rel)

        # Skip the template's own README.md (it documents the template, not the output).
        if rel_str == 'README.md':
            continue
        if source.name.endswith(('.pyc', '.pyo')):
            continue

        formatted_rel = rel_str.format(**config)
        target_rel = _retarget_top_segment(formatted_rel, template_check_name, target_integration_dir)
        target_path = target_root / target_rel

        # Default behaviour drops the integration's manifest.json.
        if not include_manifest and _is_manifest_path(_StdPath(target_rel), target_integration_dir):
            continue

        binary = source.name.endswith(BINARY_EXTENSIONS)
        tf = TemplateFile(target_path=target_path, source_path=source, binary=binary)
        if read:
            tf.read(config)
        files.append(tf)

    return files


def _retarget_top_segment(formatted_rel: str, template_check_name: str, target_dir: str) -> str:
    """Rewrite the leading path segment from ``template_check_name`` to ``target_dir``."""
    if not template_check_name or template_check_name == target_dir:
        return formatted_rel
    parts = _StdPath(formatted_rel).parts
    if parts and parts[0] == template_check_name:
        return str(_StdPath(target_dir, *parts[1:]))
    return formatted_rel


def _walk_template(root: Path) -> Iterator[Path]:
    for child in sorted(root.iterdir()):
        if child.is_dir():
            yield from _walk_template(child)
        else:
            yield child


def _is_manifest_path(target_rel: _StdPath, integration_dir_name: str) -> bool:
    return target_rel == _StdPath(integration_dir_name) / 'manifest.json'


def render(
    app: Application,
    integration_type: str,
    name: str,
    *,
    location: str | None,
    dry_run: bool,
    include_manifest: bool,
    extra_fields: dict[str, Any] | None = None,
    target_integration_dir: str | None = None,
) -> ScaffoldResult:
    """Resolve target paths, render templates in memory (or just enumerate for dry-run).

    ``target_integration_dir`` selects the on-disk directory that receives the rendered
    files (the directory whose name appears as the top-level segment of every output
    path). For ``check_only``, the ``check_name`` template variable comes from the
    prefilled manifest fields in ``extra_fields``; for every other type, both default
    to ``normalize_package_name(name)``.
    """
    extra_fields = extra_fields or {}
    root = Path(location).resolve() if location else app.repo.path
    integration_dir_name = target_integration_dir or normalize_package_name(name)
    integration_dir = root / integration_dir_name

    if integration_type != 'check_only' and integration_dir.exists():
        app.abort(f'Path `{integration_dir}` already exists!')

    config = construct_template_fields(name, integration_type, **extra_fields)

    files = collect_template_files(
        integration_type,
        root,
        config,
        target_integration_dir=integration_dir_name,
        include_manifest=include_manifest,
        read=not dry_run,
    )

    if dry_run:
        if app.quiet:
            app.display(f'Will create `{integration_dir}`')
        else:
            app.display_info(f'Will create in `{root}`:')
            _display_tree(app, root, files)
    else:
        _write_files_with_cleanup_hint(app, files, integration_dir, integration_type)
        if app.quiet:
            app.display(f'Created `{integration_dir}`')
        else:
            app.display_info(f'Created in `{root}`:')
            _display_tree(app, root, files)

    return ScaffoldResult(integration_dir=integration_dir, files=files, config=config)


def _write_files_with_cleanup_hint(
    app: Application,
    files: list[TemplateFile],
    integration_dir: Path,
    integration_type: str,
) -> None:
    """Write files and, on failure, tell the user how to recover.

    For most types, the entire integration directory was created by this run and
    is safe to delete. For ``check_only`` the directory pre-exists with the
    user's ``manifest.json`` — tell them which scaffolded files to clean up
    instead so they don't lose existing work.
    """
    total = len(files)
    written: list[Path] = []
    for index, f in enumerate(files, 1):
        try:
            f.write()
        except OSError as exc:
            base = f'Wrote {index - 1}/{total} files; failed at `{f.target_path}`: {exc}.'
            if integration_type == 'check_only':
                if written:
                    listing = '\n  - '.join(str(p) for p in written)
                    cleanup = (
                        'Remove the scaffolded files listed below (your `manifest.json` and any '
                        'other pre-existing files in the directory must be preserved) and retry:\n'
                        f'  - {listing}'
                    )
                else:
                    cleanup = 'No files were written before the failure; safe to retry directly.'
            else:
                cleanup = f'Remove `{integration_dir}` and retry.'
            app.abort(f'{base} {cleanup}')
        written.append(f.target_path)


def _display_tree(app: Application, root: Path, files: list[TemplateFile]) -> None:
    tree: defaultdict = defaultdict(dict)
    for f in files:
        try:
            rel = f.target_path.relative_to(root)
        except ValueError:
            rel = _StdPath(str(f.target_path))
        branch: dict = tree
        for part in rel.parts:
            branch = branch.setdefault(part, {})

    for indent, name, is_dir in _path_tree_output(tree):
        line = f'{indent}{name}'
        if is_dir:
            app.display_success(line)
        else:
            app.display_info(line)


def _path_tree_output(node: dict, depth: int = 0) -> Iterator[tuple[str, str, bool]]:
    dirs: list[str] = []
    files: list[str] = []
    for k, v in node.items():
        (dirs if v else files).append(k)
    dirs.sort()
    files.sort()

    total_dirs = len(dirs)
    for i, name in enumerate(dirs, 1):
        last = i == total_dirs and not files
        yield _format_line(name, depth, last=last, is_dir=True)
        yield from _path_tree_output(node[name], depth + 1)

    total_files = len(files)
    for i, name in enumerate(files, 1):
        last = i == total_files
        yield _format_line(name, depth, last=last, is_dir=False)


def _format_line(name: str, depth: int, *, last: bool, is_dir: bool) -> tuple[str, str, bool]:
    if depth == 0:
        return '', name, is_dir
    if depth == 1:
        return f'{PIPE_END if last else PIPE_MIDDLE}{HYPHEN} ', name, is_dir
    return (
        f"{PIPE}   {' ' * 4 * (depth - 2)}{PIPE_END if last else PIPE_MIDDLE}{HYPHEN} ",
        name,
        is_dir,
    )
