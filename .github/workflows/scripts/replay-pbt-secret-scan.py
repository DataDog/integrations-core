#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fail if replay validation artifacts contain high-confidence secret patterns."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REDACTED_VALUES = {'', '<REDACTED>', '***', 'REDACTED', 'redacted', 'null', 'none'}
MAX_TEXT_BYTES = 20 * 1024 * 1024

SENSITIVE_KEY_RE = re.compile(
    r'(?i)(^|[_\-.])('
    r'authorization|proxy-authorization|cookie|set-cookie|'
    r'api[_-]?key|app[_-]?key|application[_-]?key|'
    r'access[_-]?token|refresh[_-]?token|id[_-]?token|token|'
    r'secret|password|passwd|passphrase|private[_-]?key|client[_-]?secret|'
    r'credential|signature|csrf|xsrf|access[_-]?key|secret[_-]?key'
    r')($|[_\-.])'
)

KEY_VALUE_TEXT_RE = re.compile(
    r'(?ix)\b('
    r'[A-Z0-9_.-]*'
    r'(?:'
    r'authorization|proxy-authorization|cookie|set-cookie|'
    r'api[_-]?key|app[_-]?key|application[_-]?key|'
    r'access[_-]?token|refresh[_-]?token|id[_-]?token|token|'
    r'secret|password|passwd|passphrase|private[_-]?key|client[_-]?secret|'
    r'credential|signature|session'
    r')'
    r'[A-Z0-9_.-]*'
    r')\s*[:=]\s*("[^"\n]*"|[^&\s,}]+)'
)

SECRET_PATTERNS = (
    ('github-token', re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b')),
    ('github-pat', re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b')),
    ('slack-token', re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b')),
    ('aws-access-key', re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('jwt', re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b')),
    ('bearer-token', re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}={0,2}')),
    ('basic-token', re.compile(r'(?i)\bBasic\s+[A-Za-z0-9+/]{12,}={0,2}')),
    ('private-key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
)


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str
    detail: str


def is_redacted(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool | int | float):
        return True
    text = str(value).strip().strip('"\'[])}')
    return '<REDACTED>' in text or text in REDACTED_VALUES or text.lower() in REDACTED_VALUES or set(text) <= {'*'}


def iter_files(paths: list[Path]) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir():
            for child in sorted(path.rglob('*')):
                if child.is_file():
                    files.append((str(child), child.read_bytes()))
        elif zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.endswith('/'):
                        continue
                    files.append((f'{path}!{name}', archive.read(name)))
        else:
            files.append((str(path), path.read_bytes()))
    return files


def scan_json(value: Any, path: str, findings: list[Finding], json_path: str = '$') -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f'{json_path}.{key}'
            if SENSITIVE_KEY_RE.search(str(key)) and not is_redacted(child):
                findings.append(Finding(path, 'sensitive-json-key', child_path))
            scan_json(child, path, findings, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_json(child, path, findings, f'{json_path}[{index}]')


def scan_text(path: str, data: bytes) -> list[Finding]:
    findings: list[Finding] = []
    if b'\0' in data[:4096] or len(data) > MAX_TEXT_BYTES:
        return findings

    text = data.decode('utf-8', errors='replace')
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(Finding(path, name, 'matched high-confidence token pattern'))

    for match in KEY_VALUE_TEXT_RE.finditer(text):
        key = match.group(1)
        value = match.group(2)
        if not is_redacted(value):
            line = text.count('\n', 0, match.start()) + 1
            findings.append(Finding(path, 'sensitive-assignment', f'line {line}: {key}=<redacted>'))

    if path.endswith('.json'):
        try:
            scan_json(json.loads(text), path, findings)
        except Exception:
            pass

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()

    findings: list[Finding] = []
    for path, data in iter_files(args.paths):
        findings.extend(scan_text(path, data))

    if findings:
        print('Replay validation artifact secret scan failed:', file=sys.stderr)
        for finding in findings[:100]:
            print(f'- {finding.path}: {finding.kind}: {finding.detail}', file=sys.stderr)
        if len(findings) > 100:
            print(f'- ... {len(findings) - 100} more findings', file=sys.stderr)
        return 1

    print('Replay validation artifact secret scan passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
