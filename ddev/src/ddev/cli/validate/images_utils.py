# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Scanner, env-var resolver, and manifest helpers for `ddev validate images`.

Public surface:
  scan_repo(app) -> Manifest
  load_manifest(path) -> Manifest
  write_manifest(path, manifest) -> None
  diff_manifests(old, new) -> ManifestDiff
  classify(image, prefixes) -> bool
"""
from __future__ import annotations

import ast
import fnmatch
import json
import re
import tomllib
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from itertools import product
from pathlib import Path

import yaml

_ENV_VAR_RE = re.compile(
    r'''
    \$\$                                   # escaped $$ -> literal $
    | \$\{([A-Za-z_][A-Za-z0-9_]*)         # ${VAR
         (?: (:?-) ([^}]*) )?              #   optional default with :-/-
       \}
    | \$([A-Za-z_][A-Za-z0-9_]*)           # $VAR
    ''',
    re.VERBOSE,
)


def substitute_env_vars(template: str, context: dict[str, str]) -> str | None:
    """Resolve docker-compose-style env-var references in `template`.

    Returns the resolved string, or None if any reference cannot be resolved.
    """
    unresolved = False

    def repl(match: re.Match[str]) -> str:
        nonlocal unresolved
        whole = match.group(0)
        if whole == '$$':
            return '$'
        braced_name = match.group(1)
        op = match.group(2)
        default = match.group(3)
        bare_name = match.group(4)
        name = braced_name or bare_name
        value = context.get(name)
        if op == ':-':
            if not value:
                return default if default is not None else ''
            return value
        if op == '-':
            if value is None:
                return default if default is not None else ''
            return value
        if value is None:
            unresolved = True
            return ''
        return value

    result = _ENV_VAR_RE.sub(repl, template)
    return None if unresolved else result


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a docker-compose-style `.env` file. Missing file yields empty dict."""
    if not path.is_file():
        return {}
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def hatch_contexts(hatch_toml_path: Path) -> list[dict[str, str]]:
    """Return one env-var context per hatch matrix combination.

    Missing file yields a single empty context so callers can still resolve
    inline `${VAR:-default}` defaults.
    """
    if not hatch_toml_path.is_file():
        return [{}]

    data = tomllib.loads(hatch_toml_path.read_text(encoding='utf-8'))
    envs = data.get('envs', {})

    all_contexts: list[dict[str, str]] = []
    for env_cfg in envs.values():
        static = {k: str(v) for k, v in (env_cfg.get('env-vars') or {}).items()}

        matrix_entries = env_cfg.get('matrix') or []
        overrides = (env_cfg.get('overrides') or {}).get('matrix') or {}

        if not matrix_entries:
            all_contexts.append(dict(static))
            continue

        for entry in matrix_entries:
            keys = list(entry.keys())
            value_lists = [entry[k] for k in keys]
            for combo in product(*value_lists):
                ctx = dict(static)
                for k, v in zip(keys, combo, strict=True):
                    env_var_name = _override_env_var_name(overrides, k)
                    if env_var_name:
                        ctx[env_var_name] = str(v)
                all_contexts.append(ctx)

    return all_contexts or [{}]


def _override_env_var_name(overrides: dict, matrix_key: str) -> str | None:
    entry = overrides.get(matrix_key, {})
    if isinstance(entry, dict):
        name = entry.get('env-vars')
        if isinstance(name, str):
            return name
    return None


def scan_compose_file(path: Path, contexts: list[dict[str, str]]) -> Iterator[str]:
    """Yield resolved `image:tag` strings from a docker-compose file.

    Unresolved references are skipped silently at this layer; the aggregator
    is responsible for surfacing warnings.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except yaml.YAMLError:
        return

    services = data.get('services') or {}
    seen: set[str] = set()
    for service in services.values():
        if not isinstance(service, dict):
            continue
        raw = service.get('image')
        if not isinstance(raw, str):
            continue
        for ctx in contexts:
            resolved = substitute_env_vars(raw, ctx)
            if resolved is not None and resolved not in seen:
                seen.add(resolved)
                yield resolved


_ARG_RE = re.compile(r'^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)(?:=(.*))?\s*$')
_FROM_RE = re.compile(r'^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+\S+)?\s*$', re.IGNORECASE)


def scan_dockerfile(path: Path, contexts: list[dict[str, str]]) -> Iterator[str]:
    """Yield resolved image refs from FROM lines in a Dockerfile."""
    text = path.read_text(encoding='utf-8', errors='replace')
    arg_defaults: dict[str, str] = {}
    seen: set[str] = set()
    for raw_line in text.splitlines():
        if (arg_match := _ARG_RE.match(raw_line)):
            name, default = arg_match.group(1), arg_match.group(2)
            if default is not None:
                arg_defaults[name] = default
            continue
        if (from_match := _FROM_RE.match(raw_line)):
            raw_ref = from_match.group(1)
            for ctx in contexts:
                merged = {**arg_defaults, **ctx}
                resolved = substitute_env_vars(raw_ref, merged)
                if resolved and resolved not in seen:
                    seen.add(resolved)
                    yield resolved


def scan_python_fixture(path: Path) -> Iterator[str]:
    """Yield string-literal `image=` values from a Python file's AST."""
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if (
                kw.arg == 'image'
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                value = kw.value.value
                if value and value not in seen:
                    seen.add(value)
                    yield value


def split_ref(ref: str) -> tuple[str, str]:
    """Split an image reference into (image, tag). Untagged refs get 'latest'.

    Handles `host:port/path:tag` by distinguishing a port from a tag:
    the tag never contains a '/'.
    """
    last_colon = ref.rfind(':')
    if last_colon == -1:
        return ref, 'latest'
    candidate_tag = ref[last_colon + 1:]
    if '/' in candidate_tag:
        return ref, 'latest'
    return ref[:last_colon], candidate_tag


def classify(image: str, mirror_prefixes: list[str]) -> bool:
    """True when `image` starts with any configured mirror prefix."""
    return any(image.startswith(prefix) for prefix in mirror_prefixes)


@dataclass(frozen=True)
class ResolvedRef:
    ref: str
    integration: str


@dataclass
class ImageEntry:
    image: str
    mirrored: bool
    tags: list[str]
    integrations: list[str]


@dataclass
class Manifest:
    version: int = 1
    images: list[ImageEntry] = field(default_factory=list)


def aggregate(refs: list[tuple[str, str]], mirror_prefixes: list[str]) -> Manifest:
    """Group (ref, integration) pairs into a sorted Manifest."""
    per_image: dict[str, dict[str, set[str]]] = {}
    for ref, integration in refs:
        image, tag = split_ref(ref)
        entry = per_image.setdefault(image, {'tags': set(), 'integrations': set()})
        entry['tags'].add(tag)
        entry['integrations'].add(integration)

    images = [
        ImageEntry(
            image=image,
            mirrored=classify(image, mirror_prefixes),
            tags=sorted(entry['tags']),
            integrations=sorted(entry['integrations']),
        )
        for image, entry in sorted(per_image.items())
    ]
    return Manifest(version=1, images=images)


def scan_repo(
    repo_path: Path,
    integrations: list[str],
    mirror_prefixes: list[str],
    exclude_globs: list[str],
) -> Manifest:
    """Scan every source file for every integration and build a Manifest."""
    refs: list[tuple[str, str]] = []
    for integration in integrations:
        integ_root = repo_path / integration
        if not integ_root.is_dir():
            continue
        contexts = _contexts_for_integration(integ_root)
        refs.extend(_scan_integration_sources(integration, integ_root, contexts, exclude_globs))
    return aggregate(refs, mirror_prefixes)


def _contexts_for_integration(integ_root: Path) -> list[dict[str, str]]:
    contexts = hatch_contexts(integ_root / 'hatch.toml')
    env_overlays = [parse_env_file(env_file) for env_file in integ_root.rglob('.env')]
    if not env_overlays:
        return contexts
    merged: list[dict[str, str]] = []
    for ctx in contexts:
        for overlay in env_overlays:
            merged.append({**ctx, **overlay})
    return merged


def _scan_integration_sources(
    integration: str,
    integ_root: Path,
    contexts: list[dict[str, str]],
    exclude_globs: list[str],
) -> Iterator[tuple[str, str]]:
    def _excluded(path: Path) -> bool:
        rel = path.relative_to(integ_root.parent)
        return any(fnmatch.fnmatch(str(rel), g) for g in exclude_globs)

    for compose in integ_root.rglob('docker-compose*.y*ml'):
        if _excluded(compose):
            continue
        for ref in scan_compose_file(compose, contexts):
            yield ref, integration

    for dockerfile in _iter_dockerfiles(integ_root):
        if _excluded(dockerfile):
            continue
        for ref in scan_dockerfile(dockerfile, contexts):
            yield ref, integration

    for py_file in integ_root.rglob('tests/**/*.py'):
        if _excluded(py_file):
            continue
        for ref in scan_python_fixture(py_file):
            yield ref, integration


def _iter_dockerfiles(root: Path) -> Iterator[Path]:
    yield from root.rglob('Dockerfile')
    yield from root.rglob('*.Dockerfile')
    yield from root.rglob('Dockerfile.*')


@dataclass
class ManifestDiff:
    added_images: list[str] = field(default_factory=list)
    removed_images: list[str] = field(default_factory=list)
    modified_images: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.added_images or self.removed_images or self.modified_images)


def load_manifest(path: Path) -> Manifest:
    if not path.is_file():
        return Manifest()
    raw = json.loads(path.read_text(encoding='utf-8'))
    return Manifest(
        version=raw.get('version', 1),
        images=[ImageEntry(**entry) for entry in raw.get('images', [])],
    )


def write_manifest(path: Path, manifest: Manifest) -> None:
    sorted_images = sorted(manifest.images, key=lambda e: e.image)
    payload = {
        'version': manifest.version,
        'images': [asdict(e) for e in sorted_images],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + '\n', encoding='utf-8')


def diff_manifests(old: Manifest, new: Manifest) -> ManifestDiff:
    old_by_image = {e.image: e for e in old.images}
    new_by_image = {e.image: e for e in new.images}
    added = sorted(set(new_by_image) - set(old_by_image))
    removed = sorted(set(old_by_image) - set(new_by_image))
    modified = sorted(
        image
        for image in set(old_by_image) & set(new_by_image)
        if old_by_image[image] != new_by_image[image]
    )
    return ManifestDiff(added_images=added, removed_images=removed, modified_images=modified)
