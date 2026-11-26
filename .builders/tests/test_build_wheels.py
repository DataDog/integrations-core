from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import importlib
import io
import shutil
import stat
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

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


def test_kubernetes_api_docstrings_are_kept_for_watch(tmp_path: Path):
    # `kubernetes.watch.Watch` reads the API method docstrings to pick the event type and the streaming
    # argument, so only the model docstrings may be emptied.
    api = tmp_path / 'kubernetes/client/api/core_v1_api.py'
    api_source = '''class CoreV1Api:
    def read_namespaced_pod_log(self, name, namespace, **kwargs):
        """read log of the specified Pod

        :param bool follow: Follow the log stream of the pod.
        :return: str
        """
'''
    model = tmp_path / 'kubernetes/client/models/v1_pod.py'
    model_source = '''class V1Pod:
    """Pod is a collection of containers that can run on a host."""
'''
    for path, source in ((api, api_source), (model, model_source)):
        path.parent.mkdir(parents=True)
        path.write_text(source, encoding='utf-8')

    rules = build_wheels._get_matching_rules('kubernetes-35.0.0-py2.py3-none-any.whl')

    assert build_wheels._strip_lines_from_dir(tmp_path, rules)
    assert api.read_text(encoding='utf-8') == api_source
    assert 'collection of containers' not in model.read_text(encoding='utf-8')


@pytest.mark.parametrize(
    'wheel_name, strip_docstrings',
    [
        ('cm_client-45.0.4-py3-none-manylinux2014_x86_64.whl', True),
        ('ddtrace-4.16.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl', True),
        ('hazelcast_python_client-5.7.0-py3-none-any.whl', True),
        ('openstacksdk-4.18.0-py3-none-any.whl', True),
        ('redis-8.1.0-py3-none-any.whl', True),
        # A separate distribution whose docstrings were not reviewed
        ('ddtrace_internal-0.1.0-py3-none-any.whl', False),
    ],
)
def test_docstring_rules_match_wheel_filenames(wheel_name: str, strip_docstrings: bool):
    # Wheel filenames use the normalized project name (`cm-client` becomes `cm_client`), so a rule
    # written with the project name would never apply.
    rules = build_wheels._get_matching_rules(wheel_name)

    assert any(rule.get('strip_docstrings', False) for rule in rules) is strip_docstrings


ORJSON_MACOS_15 = 'orjson-3.13.0-cp313-cp313-macosx_15_0_arm64.whl'
ORJSON_UNIVERSAL = 'orjson-3.13.0-cp313-cp313-macosx_10_15_x86_64.macosx_11_0_arm64.macosx_10_15_universal2.whl'


def _write_orjson_wheel(path: Path, requires_dist: str = '') -> None:
    metadata = f'Metadata-Version: 2.1\nName: orjson\nVersion: 3.13.0\nRequires-Python: >=3.10\n{requires_dist}'
    with ZipFile(path, 'w') as wheel:
        wheel.writestr('orjson-3.13.0.dist-info/METADATA', metadata)
        wheel.writestr('orjson/__init__.py', path.name)


def _fake_pip_download(monkeypatch: pytest.MonkeyPatch, available: dict[str, str]) -> list[list[str]]:
    """Answer `pip download` with the wheels in `available`, by platform, as PyPI would for orjson 3.13.0."""
    calls: list[list[str]] = []

    def run(command_args: list[str], **_kwargs: Any) -> SimpleNamespace:
        calls.append(command_args)
        platform = command_args[command_args.index('--platform') + 1]
        if platform not in available:
            return SimpleNamespace(returncode=1)

        destination = Path(command_args[command_args.index('--dest') + 1])
        _write_orjson_wheel(destination / ORJSON_UNIVERSAL, available[platform])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(build_wheels.subprocess, 'run', run)
    monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', '12.0')
    # The host CPU architecture is a platform boundary: pin it so the result doesn't depend on the machine
    monkeypatch.setattr(build_wheels.os, 'uname', lambda: SimpleNamespace(machine='arm64'), raising=False)
    return calls


def test_use_macos_target_wheels_replaces_wheel_needing_newer_macos_with_compatible_wheel_of_same_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    compatible = tmp_path / 'six-1.17.0-py2.py3-none-any.whl'
    compatible.write_bytes(b'untouched')
    _write_orjson_wheel(tmp_path / ORJSON_MACOS_15)
    calls = _fake_pip_download(monkeypatch, {'macosx_12_0_arm64': ''})

    build_wheels.use_macos_target_wheels(tmp_path, Path('python'), {'PIP_NO_BINARY': 'ddtrace'})

    assert sorted(path.name for path in tmp_path.iterdir()) == sorted([ORJSON_UNIVERSAL, compatible.name])
    assert compatible.read_bytes() == b'untouched'
    assert [call[call.index('download') + 1] for call in calls] == ['orjson==3.13.0']


def test_use_macos_target_wheels_keeps_wheel_when_release_has_no_compatible_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_orjson_wheel(tmp_path / ORJSON_MACOS_15)
    _fake_pip_download(monkeypatch, {})

    build_wheels.use_macos_target_wheels(tmp_path, Path('python'), {})

    assert [path.name for path in tmp_path.iterdir()] == [ORJSON_MACOS_15]


def test_use_macos_target_wheels_rejects_replacement_declaring_different_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_orjson_wheel(tmp_path / ORJSON_MACOS_15)
    _fake_pip_download(monkeypatch, {'macosx_12_0_arm64': 'Requires-Dist: typing-extensions\n'})

    with pytest.raises(RuntimeError, match='Requires-Dist'):
        build_wheels.use_macos_target_wheels(tmp_path, Path('python'), {})


def _compile_test_shared_library(output_path: Path, *, extra_flags: list[str]) -> None:
    source = output_path.with_suffix('.c')
    source.write_text('int add(int a, int b) { return a + b; }\n', encoding='utf-8')
    subprocess.check_call(['gcc', '-shared', '-fPIC', *extra_flags, str(source), '-o', str(output_path)])


def _fake_elf64_header(*, e_type: int, e_machine: int) -> bytes:
    header = bytearray(build_wheels.ELF_HEADER_SIZE)
    header[0:4] = build_wheels.ELF_MAGIC
    header[4] = build_wheels.ELF_CLASS_64
    header[5] = build_wheels.ELF_DATA_LSB
    header[6] = build_wheels.ELF_VERSION_CURRENT
    struct.pack_into('<HH', header, 16, e_type, e_machine)
    return bytes(header)


def _write_elf_wheel(
    wheel_path: Path,
    so_bytes: bytes,
    *,
    so_relpath: str = 'sample/_ext.cpython-313-x86_64-linux-gnu.so',
    so_mode: int = 0o755,
    so_file_type: int = stat.S_IFREG,
) -> None:
    dist_info = 'sample-1.0.0.dist-info'
    record_path = f'{dist_info}/RECORD'
    files = {
        so_relpath: so_bytes,
        f'{dist_info}/METADATA': b'Metadata-Version: 2.1\nName: sample\nVersion: 1.0.0\n',
        f'{dist_info}/WHEEL': (
            b'Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: false\n'
            b'Tag: cp313-cp313-manylinux2014_x86_64\n'
        ),
    }
    with ZipFile(wheel_path, 'w', compression=ZIP_DEFLATED) as wheel:
        for name, contents in files.items():
            if name == so_relpath:
                info = ZipInfo(name)
                info.compress_type = ZIP_DEFLATED
                info.external_attr = (so_file_type | so_mode) << 16
                wheel.writestr(info, contents)
            else:
                wheel.writestr(name, contents)
        wheel.writestr(record_path, _record_contents(files, record_path))


@pytest.mark.skipif(
    sys.platform != 'linux' or not all(shutil.which(tool) for tool in ('gcc', 'readelf', 'strip')),
    reason='Requires Linux binutils and gcc',
)
@pytest.mark.parametrize(
    'so_relpath',
    [
        'sample/_ext.cpython-313-x86_64-linux-gnu.so',
        'sample.libs/libfoo-deadbeef.so.1.2',
    ],
)
def test_clean_wheel_strips_elf_debug_info_and_updates_record(tmp_path: Path, so_relpath: str):
    so_path = tmp_path / '_ext.so'
    _compile_test_shared_library(so_path, extra_flags=['-g'])
    original_so_bytes = so_path.read_bytes()
    assert build_wheels._elf_has_debug_sections(so_path)

    wheel_path = tmp_path / 'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl'
    _write_elf_wheel(wheel_path, original_so_bytes, so_relpath=so_relpath, so_mode=0o555)

    assert build_wheels.clean_wheel(wheel_path)

    with ZipFile(wheel_path) as wheel:
        stripped_so_bytes = wheel.read(so_relpath)
        so_info = wheel.getinfo(so_relpath)
        record_rows = {
            row[0]: row
            for row in csv.reader(io.TextIOWrapper(wheel.open('sample-1.0.0.dist-info/RECORD'), encoding='utf-8'))
        }

    assert len(stripped_so_bytes) < len(original_so_bytes)
    assert stat.S_IMODE(so_info.external_attr >> 16) == 0o555

    stripped_so_path = tmp_path / '_ext_stripped.so'
    stripped_so_path.write_bytes(stripped_so_bytes)
    assert not build_wheels._elf_has_debug_sections(stripped_so_path)

    expected_digest = base64.urlsafe_b64encode(hashlib.sha256(stripped_so_bytes).digest()).rstrip(b'=').decode()
    assert record_rows[so_relpath] == [so_relpath, f'sha256={expected_digest}', str(len(stripped_so_bytes))]
    assert not build_wheels.clean_wheel(wheel_path)


@pytest.mark.skipif(
    sys.platform != 'linux' or not all(shutil.which(tool) for tool in ('gcc', 'readelf', 'strip')),
    reason='Requires Linux binutils and gcc',
)
def test_clean_wheel_leaves_already_stripped_elf_wheel_unchanged(tmp_path: Path):
    so_path = tmp_path / '_ext.so'
    _compile_test_shared_library(so_path, extra_flags=['-Wl,--strip-debug'])
    assert not build_wheels._elf_has_debug_sections(so_path)

    wheel_path = tmp_path / 'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl'
    _write_elf_wheel(wheel_path, so_path.read_bytes())
    original_wheel_bytes = wheel_path.read_bytes()

    assert not build_wheels.clean_wheel(wheel_path)
    assert wheel_path.read_bytes() == original_wheel_bytes


@pytest.mark.parametrize(
    'wheel_name, so_relpath, so_bytes, so_file_type',
    [
        pytest.param(
            'sample-1.0.0-py3-none-any.whl',
            'sample/_ext.so',
            _fake_elf64_header(e_type=build_wheels.ELF_TYPE_DYN, e_machine=62),
            stat.S_IFREG,
            id='pure-python-wheel',
        ),
        pytest.param(
            'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl',
            'sample/libfoo.so.debug',
            _fake_elf64_header(e_type=build_wheels.ELF_TYPE_DYN, e_machine=62),
            stat.S_IFREG,
            id='non-numeric-so-suffix',
        ),
        pytest.param(
            'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl',
            'sample/_ext.so',
            b'\x7fELFnot-a-real-elf',
            stat.S_IFREG,
            id='truncated-elf-magic',
        ),
        pytest.param(
            'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl',
            'sample/_ext.so',
            _fake_elf64_header(e_type=build_wheels.ELF_TYPE_DYN, e_machine=183),
            stat.S_IFREG,
            id='foreign-architecture-elf',
        ),
        pytest.param(
            'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl',
            'sample/_ext.so',
            _fake_elf64_header(e_type=1, e_machine=62),
            stat.S_IFREG,
            id='non-shared-object-elf',
        ),
        pytest.param(
            'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl',
            'sample/_ext.so',
            _fake_elf64_header(e_type=build_wheels.ELF_TYPE_DYN, e_machine=62),
            stat.S_IFLNK,
            id='symlink-shared-object',
        ),
    ],
)
def test_clean_wheel_ignores_non_host_shared_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wheel_name: str,
    so_relpath: str,
    so_bytes: bytes,
    so_file_type: int,
):
    wheel_path = tmp_path / wheel_name
    _write_elf_wheel(wheel_path, so_bytes, so_relpath=so_relpath, so_file_type=so_file_type)
    original_wheel_bytes = wheel_path.read_bytes()

    monkeypatch.setattr(build_wheels.sys, 'platform', 'linux')
    monkeypatch.setattr(build_wheels.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(
        build_wheels,
        'unpack_wheel',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('should not unpack wheel')),
    )
    monkeypatch.setattr(
        build_wheels.subprocess,
        'run',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('should not run subprocess')),
    )

    assert not build_wheels.clean_wheel(wheel_path)
    assert wheel_path.read_bytes() == original_wheel_bytes


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_clean_wheel_skips_elf_stripping_on_non_linux(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str
):
    wheel_path = tmp_path / 'sample-1.0.0-cp313-cp313-manylinux2014_x86_64.whl'
    _write_elf_wheel(wheel_path, _fake_elf64_header(e_type=build_wheels.ELF_TYPE_DYN, e_machine=62))
    original_wheel_bytes = wheel_path.read_bytes()

    monkeypatch.setattr(build_wheels.sys, 'platform', platform)
    monkeypatch.setattr(build_wheels.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(
        build_wheels,
        'unpack_wheel',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('should not unpack wheel')),
    )
    monkeypatch.setattr(
        build_wheels.subprocess,
        'run',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('should not run subprocess')),
    )

    assert not build_wheels.clean_wheel(wheel_path)
    assert wheel_path.read_bytes() == original_wheel_bytes
