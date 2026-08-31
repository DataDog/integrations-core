import csv
import importlib
import io
import shutil
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
from zipfile import ZipInfo

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
repair_wheels = importlib.import_module('repair_wheels')


LIBDDWAF_PATH = 'ddtrace/appsec/_ddwaf/libddwaf/x86_64/lib/libddwaf.dylib'
MODULE_PATH = 'ddtrace/__init__.py'


def write_wheel(path: Path) -> None:
    record_path = f'{path.name.split("-")[0]}-1.0.0.dist-info/RECORD'
    entries = [(MODULE_PATH, b'package contents')]
    entries.append((LIBDDWAF_PATH, b'incompatible dylib'))

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


def test_repair_linux_excludes_agent_provided_libraries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_built_dir = tmp_path / 'source-built'
    source_external_dir = tmp_path / 'source-external'
    built_dir = tmp_path / 'built'
    external_dir = tmp_path / 'external'
    for directory in (source_built_dir, source_external_dir, built_dir, external_dir):
        directory.mkdir()
    (source_built_dir / 'package-1.0.0-cp313-cp313-linux_x86_64.whl').touch()

    captured_exclusions: list[frozenset[str]] = []

    class FakePolicies:
        def get_policy_by_name(self, name: str) -> dict:
            assert name == 'manylinux2014_x86_64'
            return {
                'name': name,
                'aliases': [],
                'lib_whitelist': ['libz.so.1'],
                'symbol_versions': {'ZLIB': []},
            }

    class NonPlatformWheel(Exception):
        pass

    def fake_repair_wheel(*_args, exclude: frozenset[str], **_kwargs) -> None:
        captured_exclusions.append(exclude)

    auditwheel = ModuleType('auditwheel')
    auditwheel.__path__ = []
    monkeypatch.setitem(sys.modules, 'auditwheel', auditwheel)
    monkeypatch.setitem(sys.modules, 'auditwheel.patcher', SimpleNamespace(Patchelf=object))
    monkeypatch.setitem(sys.modules, 'auditwheel.policy', SimpleNamespace(WheelPolicies=FakePolicies))
    monkeypatch.setitem(sys.modules, 'auditwheel.repair', SimpleNamespace(repair_wheel=fake_repair_wheel))
    monkeypatch.setitem(sys.modules, 'auditwheel.wheel_abi', SimpleNamespace(NonPlatformWheel=NonPlatformWheel))
    monkeypatch.setenv('MANYLINUX_POLICY', 'manylinux2014_x86_64')

    repair_wheels.repair_linux(
        str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
    )

    assert captured_exclusions == [frozenset({'libmqic_r.so', 'libcurl.so.4', 'libodbc.so.2'})]


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
