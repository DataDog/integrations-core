from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import importlib
import io
import sys
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
build_wheels = importlib.import_module('build_wheels')


DIST_INFO = 'psycopg_c-1.0.0.dist-info'
RECORD_PATH = f'{DIST_INFO}/RECORD'
REMOVED_PATHS = {
    'psycopg_c/_psycopg.c',
    'psycopg_c/pq.c',
    'psycopg_c/types/numutils.c',
    'psycopg_c/future/generated.c',
}
PRESERVED_FILES = {
    'psycopg_c/_psycopg.cpython-313-x86_64-linux-gnu.so': b'compiled extension',
    'psycopg_c/_psycopg.pyi': b'class Connection: ...\n',
    'psycopg_c/pq.pxd': b'cdef int libpq_version\n',
    'other/_psycopg.c': b'/* unrelated source */\n',
}


def _record_contents(files: dict[str, bytes], record_path: str = RECORD_PATH) -> bytes:
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    for path, contents in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b'=').decode()
        writer.writerow((path, f'sha256={digest}', len(contents)))
    writer.writerow((record_path, '', ''))
    return output.getvalue().encode()


def _write_psycopg_wheel(path: Path) -> None:
    files = {
        **PRESERVED_FILES,
        'psycopg_c/_psycopg.c': b'/* generated extension source */\n',
        'psycopg_c/pq.c': b'/* generated pq source */\n',
        'psycopg_c/types/numutils.c': b'/* supporting extension source */\n',
        'psycopg_c/future/generated.c': b'/* future extension source */\n',
        f'{DIST_INFO}/METADATA': b'Metadata-Version: 2.1\nName: psycopg-c\nVersion: 1.0.0\n',
        f'{DIST_INFO}/WHEEL': (b'Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: false\nTag: py3-none-any\n'),
    }
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as wheel:
        for name, contents in files.items():
            wheel.writestr(name, contents)
        wheel.writestr(RECORD_PATH, _record_contents(files))


def test_clean_wheel_removes_all_psycopg_c_sources(tmp_path: Path):
    wheel_path = tmp_path / 'psycopg_c-1.0.0-py3-none-any.whl'
    _write_psycopg_wheel(wheel_path)

    assert build_wheels.clean_wheel(wheel_path)

    with ZipFile(wheel_path) as wheel:
        installed_paths = set(wheel.namelist())
        record_rows = list(csv.reader(io.TextIOWrapper(wheel.open(RECORD_PATH), encoding='utf-8')))

    assert REMOVED_PATHS.isdisjoint(installed_paths)
    assert PRESERVED_FILES.keys() <= installed_paths

    recorded_paths = {row[0] for row in record_rows}
    assert REMOVED_PATHS.isdisjoint(recorded_paths)
    assert PRESERVED_FILES.keys() <= recorded_paths


def test_clean_wheel_removes_jsonpatch_console_scripts(tmp_path: Path):
    dist_info = 'jsonpatch-1.35.dist-info'
    record_path = f'{dist_info}/RECORD'
    removed = {f'{dist_info}/entry_points.txt', 'jsonpatch_cli.py'}
    files = {
        'jsonpatch.py': b'def make_patch(src, dst): ...\n',
        'jsonpatch_cli.py': b'def jsonpatch_main(): ...\n',
        f'{dist_info}/entry_points.txt': b'[console_scripts]\njsonpatch = jsonpatch_cli:jsonpatch_main\n',
        f'{dist_info}/METADATA': b'Metadata-Version: 2.1\nName: jsonpatch\nVersion: 1.35\n',
        f'{dist_info}/WHEEL': b'Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
    }
    wheel_path = tmp_path / 'jsonpatch-1.35-py3-none-any.whl'
    with ZipFile(wheel_path, 'w', compression=ZIP_DEFLATED) as wheel:
        for name, contents in files.items():
            wheel.writestr(name, contents)
        wheel.writestr(record_path, _record_contents(files, record_path))

    assert build_wheels.clean_wheel(wheel_path)

    with ZipFile(wheel_path) as wheel:
        installed_paths = set(wheel.namelist())
        recorded_paths = {row[0] for row in csv.reader(io.TextIOWrapper(wheel.open(record_path), encoding='utf-8'))}

    assert removed.isdisjoint(installed_paths)
    assert removed.isdisjoint(recorded_paths)
    assert 'jsonpatch.py' in installed_paths
    assert 'jsonpatch.py' in recorded_paths


@pytest.mark.parametrize('newline', ['\n', '\r\n'])
@pytest.mark.parametrize('strip_docstrings', [True, False])
def test_docstring_trimming_preserves_runtime_strings_and_python_syntax(
    tmp_path: Path, newline: str, strip_docstrings: bool
):
    # Removing documentation must preserve future imports, empty bodies, and runtime string literals.
    source = '''# Copyright remains in the packaged source.
"""Module documentation."""
from __future__ import annotations

MESSAGE = """This string is runtime data."""

class Client:
    """Class documentation."""

    def query(self):
        """Method documentation
        with more than one line.
        """
        return MESSAGE

def café(): """Inline documentation."""; return "résultat"

async def query_async():
    """Async documentation."""
    return MESSAGE

def placeholder():
    """A docstring-only body."""
'''
    path = tmp_path / 'client.py'
    path.write_bytes(source.replace('\n', newline).encode('utf-8'))
    rules = [
        dict(rule, strip_docstrings=strip_docstrings)
        for rule in build_wheels._get_matching_rules('pymongo-4.18.2-py3-none-any.whl')
    ]

    assert build_wheels._strip_lines_from_dir(tmp_path, rules) is strip_docstrings

    updated = path.read_text(encoding='utf-8')
    namespace: dict[str, Any] = {}
    exec(compile(updated, str(path), 'exec'), namespace)
    assert updated.startswith('# Copyright remains in the packaged source.\n')
    assert namespace['Client']().query() == 'This string is runtime data.'
    assert namespace['café']() == 'résultat'
    assert namespace['placeholder']() is None
    assert asyncio.run(namespace['query_async']()) == 'This string is runtime data.'
    assert namespace['__doc__'] == ('' if strip_docstrings else 'Module documentation.')
    assert namespace['Client'].__doc__ == ('' if strip_docstrings else 'Class documentation.')
    assert namespace['query_async'].__doc__ == ('' if strip_docstrings else 'Async documentation.')
    if not strip_docstrings:
        assert path.read_bytes() == source.replace('\n', newline).encode('utf-8')
