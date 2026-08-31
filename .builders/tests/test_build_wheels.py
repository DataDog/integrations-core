from __future__ import annotations

import base64
import csv
import hashlib
import importlib
import io
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


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


def _record_contents(files: dict[str, bytes]) -> bytes:
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    for path, contents in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b'=').decode()
        writer.writerow((path, f'sha256={digest}', len(contents)))
    writer.writerow((RECORD_PATH, '', ''))
    return output.getvalue().encode()


def _write_psycopg_wheel(path: Path) -> None:
    files = {
        **PRESERVED_FILES,
        'psycopg_c/_psycopg.c': b'/* generated extension source */\n',
        'psycopg_c/pq.c': b'/* generated pq source */\n',
        'psycopg_c/types/numutils.c': b'/* supporting extension source */\n',
        'psycopg_c/future/generated.c': b'/* future extension source */\n',
        f'{DIST_INFO}/METADATA': b'Metadata-Version: 2.1\nName: psycopg-c\nVersion: 1.0.0\n',
        f'{DIST_INFO}/WHEEL': (
            b'Wheel-Version: 1.0\n'
            b'Generator: test\n'
            b'Root-Is-Purelib: false\n'
            b'Tag: py3-none-any\n'
        ),
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
