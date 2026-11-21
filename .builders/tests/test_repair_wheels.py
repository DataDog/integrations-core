import csv
import importlib
import io
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
from zipfile import ZipInfo

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
repair_wheels = importlib.import_module('repair_wheels')


LIBDDWAF_PATH = 'ddtrace/appsec/_ddwaf/libddwaf/x86_64/lib/libddwaf.dylib'
MODULE_PATH = 'ddtrace/__init__.py'


def write_wheel(path: Path, entries: list[tuple[str, bytes]] | None = None) -> None:
    record_path = f'{path.name.split("-")[0]}-1.0.0.dist-info/RECORD'
    if entries is None:
        entries = [(MODULE_PATH, b'package contents'), (LIBDDWAF_PATH, b'incompatible dylib')]

    record = io.StringIO(newline='')
    writer = csv.writer(record, lineterminator='\n')
    for name, contents in entries:
        writer.writerow((name, 'sha256=placeholder', str(len(contents))))
    writer.writerow((record_path, '', ''))

    with ZipFile(path, 'w') as wheel:
        for name, contents in entries:
            info = ZipInfo(name, date_time=(2024, 1, 2, 3, 4, 6))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            wheel.writestr(info, contents)
        wheel.writestr(record_path, record.getvalue())


def test_strip_macos_ddtrace_libddwaf_removes_only_dylib_and_record_entry(tmp_path: Path) -> None:
    wheel_path = tmp_path / 'ddtrace-1.0.0-cp313-cp313-macosx_12_0_arm64.whl'
    write_wheel(wheel_path)

    with ZipFile(wheel_path) as wheel:
        original_module_info = wheel.getinfo(MODULE_PATH)

    removed = repair_wheels._strip_macos_ddtrace_libddwaf(wheel_path)

    assert removed == [LIBDDWAF_PATH]
    with ZipFile(wheel_path) as wheel:
        assert LIBDDWAF_PATH not in wheel.namelist()
        assert wheel.read(MODULE_PATH) == b'package contents'
        assert wheel.getinfo(MODULE_PATH).date_time == original_module_info.date_time
        assert wheel.getinfo(MODULE_PATH).external_attr == original_module_info.external_attr
        record_path = next(name for name in wheel.namelist() if name.endswith('.dist-info/RECORD'))
        record_rows = list(csv.reader(io.TextIOWrapper(wheel.open(record_path), encoding='utf-8')))
        assert all(row[0] != LIBDDWAF_PATH for row in record_rows)


def test_strip_macos_ddtrace_libddwaf_leaves_other_projects_unchanged(tmp_path: Path) -> None:
    wheel_path = tmp_path / 'other-1.0.0-cp313-cp313-macosx_12_0_arm64.whl'
    write_wheel(wheel_path)
    original_contents = wheel_path.read_bytes()

    removed = repair_wheels._strip_macos_ddtrace_libddwaf(wheel_path)

    assert removed == []
    assert wheel_path.read_bytes() == original_contents


def test_repair_darwin_strips_libddwaf_before_delocate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_built_dir = tmp_path / 'source-built'
    source_external_dir = tmp_path / 'source-external'
    built_dir = tmp_path / 'built'
    external_dir = tmp_path / 'external'
    for directory in (source_built_dir, source_external_dir, built_dir, external_dir):
        directory.mkdir()

    wheel_path = source_built_dir / 'ddtrace-1.0.0-cp313-cp313-macosx_12_0_arm64.whl'
    write_wheel(wheel_path)
    delocate_saw_members = []

    def fake_delocate_wheel(source: str, destination: str, **_kwargs) -> set[str]:
        with ZipFile(source) as wheel:
            delocate_saw_members.extend(wheel.namelist())
        shutil.copyfile(source, destination)
        return set()

    monkeypatch.setitem(sys.modules, 'delocate', SimpleNamespace(delocate_wheel=fake_delocate_wheel))
    monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', '12.0')

    repair_wheels.repair_darwin(
        str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
    )

    assert LIBDDWAF_PATH not in delocate_saw_members
    with ZipFile(built_dir / wheel_path.name) as wheel:
        assert LIBDDWAF_PATH not in wheel.namelist()


def test_repair_darwin_given_external_wheel_needing_newer_macos_than_target_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_built_dir = tmp_path / 'source-built'
    source_external_dir = tmp_path / 'source-external'
    built_dir = tmp_path / 'built'
    external_dir = tmp_path / 'external'
    for directory in (source_built_dir, source_external_dir, built_dir, external_dir):
        directory.mkdir()

    # PyPI's macOS 15-only orjson wheel, which pip prefers on a macos-15 arm64 runner
    wheel_path = source_external_dir / 'orjson-3.13.0-cp313-cp313-macosx_15_0_arm64.whl'
    write_wheel(wheel_path)

    # delocate is a macOS-only native tool that isn't under test here
    monkeypatch.setitem(sys.modules, 'delocate', SimpleNamespace(delocate_wheel=None))
    monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', '12.0')
    # The host CPU architecture is a platform boundary: pin it so the result doesn't depend on the machine
    monkeypatch.setattr(repair_wheels.os, 'uname', lambda: SimpleNamespace(machine='arm64'))

    with pytest.raises(RuntimeError, match=r'orjson-3\.13\.0-cp313-cp313-macosx_15_0_arm64\.whl'):
        repair_wheels.repair_darwin(
            str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
        )


def test_repair_darwin_given_external_wheel_with_one_compatible_compressed_tag_keeps_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_built_dir = tmp_path / 'source-built'
    source_external_dir = tmp_path / 'source-external'
    built_dir = tmp_path / 'built'
    external_dir = tmp_path / 'external'
    for directory in (source_built_dir, source_external_dir, built_dir, external_dir):
        directory.mkdir()

    # PyPI's universal orjson wheel: only one of its compressed tags matches an arm64 host on macOS 12
    wheel_path = (
        source_external_dir
        / 'orjson-3.13.0-cp313-cp313-macosx_10_15_x86_64.macosx_11_0_arm64.macosx_10_15_universal2.whl'
    )
    write_wheel(wheel_path)
    original_contents = wheel_path.read_bytes()

    # delocate is a macOS-only native tool that isn't under test here
    monkeypatch.setitem(sys.modules, 'delocate', SimpleNamespace(delocate_wheel=None))
    monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', '12.0')
    # The host CPU architecture is a platform boundary: pin it so the result doesn't depend on the machine
    monkeypatch.setattr(repair_wheels.os, 'uname', lambda: SimpleNamespace(machine='arm64'))

    repair_wheels.repair_darwin(
        str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
    )

    assert (external_dir / wheel_path.name).read_bytes() == original_contents


def test_repair_darwin_repairs_external_ddtrace_and_preserves_other_external_wheels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_built_dir = tmp_path / 'source-built'
    source_external_dir = tmp_path / 'source-external'
    built_dir = tmp_path / 'built'
    external_dir = tmp_path / 'external'
    for directory in (source_built_dir, source_external_dir, built_dir, external_dir):
        directory.mkdir()

    ddtrace_wheel = source_external_dir / 'ddtrace-1.0.0-cp313-cp313-macosx_12_0_arm64.whl'
    other_wheel = source_external_dir / 'other-1.0.0-cp313-cp313-macosx_12_0_arm64.whl'
    write_wheel(ddtrace_wheel)
    write_wheel(other_wheel)
    original_other_contents = other_wheel.read_bytes()
    repaired_wheels = []

    def fake_delocate_wheel(source: str, destination: str, **_kwargs) -> set[str]:
        repaired_wheels.append(Path(source).name)
        with ZipFile(source) as wheel:
            assert LIBDDWAF_PATH not in wheel.namelist()
        shutil.copyfile(source, destination)
        return set()

    monkeypatch.setitem(sys.modules, 'delocate', SimpleNamespace(delocate_wheel=fake_delocate_wheel))
    monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', '12.0')
    # The arm64 external wheels must pass the macOS target check: pin the host CPU architecture
    monkeypatch.setattr(repair_wheels.os, 'uname', lambda: SimpleNamespace(machine='arm64'))

    repair_wheels.repair_darwin(
        str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
    )

    assert repaired_wheels == [ddtrace_wheel.name]
    assert not (external_dir / ddtrace_wheel.name).exists()
    with ZipFile(built_dir / ddtrace_wheel.name) as wheel:
        assert LIBDDWAF_PATH not in wheel.namelist()
        record_path = next(name for name in wheel.namelist() if name.endswith('.dist-info/RECORD'))
        record_rows = list(csv.reader(io.TextIOWrapper(wheel.open(record_path), encoding='utf-8')))
        assert all(row[0] != LIBDDWAF_PATH for row in record_rows)
    assert (external_dir / other_wheel.name).read_bytes() == original_other_contents


ELF_TOOLS_AVAILABLE = sys.platform.startswith('linux') and shutil.which('cc') is not None
requires_elf_tools = pytest.mark.skipif(not ELF_TOOLS_AVAILABLE, reason='requires building ELF files with cc')


def compile_shared_library(path: Path, source: str, *args: str) -> None:
    subprocess.run(
        ['cc', '-shared', '-fPIC', '-o', str(path), '-x', 'c', '-', *args], input=source.encode(), check=True
    )


@pytest.fixture
def fake_libcrypto(tmp_path: Path) -> Path:
    """A `libcrypto.so.3` stand-in exporting one symbol at `OPENSSL_3.0.0` and one at a far-future version."""
    openssl_dir = tmp_path / 'openssl'
    openssl_dir.mkdir()
    version_script = openssl_dir / 'libcrypto.map'
    version_script.write_text(
        'OPENSSL_3.0.0 { global: dd_openssl_marker; local: *; };\n'
        'OPENSSL_9.9.0 { global: dd_openssl_newer; } OPENSSL_3.0.0;\n'
    )
    library = openssl_dir / 'libcrypto.so.3'
    compile_shared_library(
        library,
        'int dd_openssl_marker(void) { return 42; }\nint dd_openssl_newer(void) { return 43; }\n',
        '-Wl,-soname,libcrypto.so.3',
        f'-Wl,--version-script={version_script}',
    )
    return library


def write_openssl_dependent_wheel(tmp_path: Path, fake_libcrypto: Path, path_in_wheel: str, symbol: str) -> Path:
    library = tmp_path / 'dependent.so'
    compile_shared_library(
        library,
        f'int {symbol}(void);\nint call_openssl(void) {{ return {symbol}(); }}\n',
        f'-L{fake_libcrypto.parent}',
        '-l:libcrypto.so.3',
    )
    wheel_path = tmp_path / 'pkg-1.0.0-cp313-cp313-manylinux2014_x86_64.whl'
    write_wheel(wheel_path, [(path_in_wheel, library.read_bytes())])
    return wheel_path


@requires_elf_tools
@pytest.mark.skipif(shutil.which('patchelf') is None, reason='requires patchelf')
@pytest.mark.parametrize('path_in_wheel', ['_ext.so', 'pkg.libs/libdep.so', 'pkg/hazmat/bindings/_ext.so'])
def test_link_agent_openssl_makes_wheel_load_agent_openssl(tmp_path: Path, fake_libcrypto: Path, path_in_wheel):
    from auditwheel.patcher import Patchelf

    wheel_path = write_openssl_dependent_wheel(tmp_path, fake_libcrypto, path_in_wheel, 'dd_openssl_marker')

    assert repair_wheels.link_agent_openssl(wheel_path, Patchelf()) == [path_in_wheel]

    # Install the wheel where the Agent does, next to the Agent's OpenSSL
    agent_lib_dir = tmp_path / 'agent' / 'embedded' / 'lib'
    site_packages = agent_lib_dir / 'python3.13' / 'site-packages'
    with ZipFile(wheel_path) as wheel:
        wheel.extractall(site_packages)
    shutil.copy(fake_libcrypto, agent_lib_dir / 'libcrypto.so.3')

    # Load in a fresh interpreter so that no other libcrypto.so.3 is already loaded. The system's libcrypto.so.3
    # doesn't export the stand-in's symbol, so loading only succeeds if the Agent's copy is found.
    code = 'import ctypes, os, sys; print(ctypes.CDLL(sys.argv[1], mode=os.RTLD_NOW).call_openssl())'
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-c', code, str(site_packages / path_in_wheel)], capture_output=True, text=True
    )
    assert result.stdout.strip() == '42', result.stderr


@requires_elf_tools
def test_find_agent_openssl_dependents_rejects_symbols_newer_than_agent_openssl(tmp_path: Path, fake_libcrypto: Path):
    wheel_path = write_openssl_dependent_wheel(tmp_path, fake_libcrypto, 'pkg/_ext.so', 'dd_openssl_newer')

    with pytest.raises(RuntimeError, match=r'pkg/_ext\.so: OPENSSL_9\.9\.0'):
        repair_wheels.find_agent_openssl_dependents(wheel_path)
