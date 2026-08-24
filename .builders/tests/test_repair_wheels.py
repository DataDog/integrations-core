import csv
import importlib
import io
import shutil
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


def write_wheel(path: Path, dylib_path: str | None = LIBDDWAF_PATH) -> None:
    record_path = f'{path.name.split("-")[0]}-1.0.0.dist-info/RECORD'
    entries = [(MODULE_PATH, b'package contents')]
    if dylib_path is not None:
        entries.append((dylib_path, b'incompatible dylib'))

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


# Layouts ddtrace could plausibly move the bundled dylib to. Every one of these makes
# MACOS_DDTRACE_LIBDDWAF_PATTERN match nothing. Before the guard that was silent: the strip
# returned [], the verification it guarded never ran, and the wheel shipped with the dylib
# intact and a green build. The Agent's macOS ABI gate does not backstop it either, because it
# allow-lists libddwaf.dylib by name -- so the two safety nets share the same blind spot.
RELOCATED_LIBDDWAF_PATHS = [
    'ddtrace/appsec/_ddwaf/libddwaf/x86_64/lib64/libddwaf.dylib',
    'ddtrace/appsec/_ddwaf/libddwaf/lib/libddwaf.dylib',
    'ddtrace/appsec/_ddwaf/libddwaf/x86_64/lib/libddwaf.1.30.dylib',
    'ddtrace/internal/libddwaf.dylib',
]


def _repair_dirs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    dirs = tuple(tmp_path / name for name in ('source-built', 'source-external', 'built', 'external'))
    for directory in dirs:
        directory.mkdir()
    return dirs


def _stub_delocate(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_delocate_wheel(source: str, destination: str, **_kwargs) -> set[str]:
        shutil.copyfile(source, destination)
        return set()

    monkeypatch.setitem(sys.modules, 'delocate', SimpleNamespace(delocate_wheel=fake_delocate_wheel))
    monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', '12.0')


def test_guard_pattern_is_broader_than_the_strip_pattern() -> None:
    # The guard only backstops the strip if everything the strip targets also trips the guard.
    from fnmatch import fnmatch

    assert fnmatch(LIBDDWAF_PATH, repair_wheels.MACOS_DDTRACE_LIBDDWAF_PATTERN)
    for path in [LIBDDWAF_PATH, *RELOCATED_LIBDDWAF_PATHS]:
        assert fnmatch(path, repair_wheels.MACOS_DDTRACE_LIBDDWAF_GUARD_PATTERN), path


@pytest.mark.parametrize('dylib_path', RELOCATED_LIBDDWAF_PATHS)
def test_repair_darwin_fails_when_libddwaf_moves_out_from_under_the_strip_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dylib_path: str
) -> None:
    source_built_dir, source_external_dir, built_dir, external_dir = _repair_dirs(tmp_path)
    write_wheel(source_built_dir / 'ddtrace-1.0.0-cp313-cp313-macosx_12_0_arm64.whl', dylib_path)
    _stub_delocate(monkeypatch)

    with pytest.raises(RuntimeError, match='still bundles libddwaf'):
        repair_wheels.repair_darwin(
            str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
        )


@pytest.mark.parametrize('dylib_path', RELOCATED_LIBDDWAF_PATHS)
def test_repair_darwin_routes_external_ddtrace_with_relocated_libddwaf_through_the_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dylib_path: str
) -> None:
    # External ddtrace wheels are routed to the built directory only if they look like they
    # bundle libddwaf. Detecting that with the narrow pattern would send a relocated dylib
    # straight to external_dir, bypassing both the strip and the guard.
    source_built_dir, source_external_dir, built_dir, external_dir = _repair_dirs(tmp_path)
    write_wheel(source_external_dir / 'ddtrace-1.0.0-cp313-cp313-macosx_12_0_arm64.whl', dylib_path)
    _stub_delocate(monkeypatch)

    with pytest.raises(RuntimeError, match='still bundles libddwaf'):
        repair_wheels.repair_darwin(
            str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
        )


def test_repair_darwin_accepts_ddtrace_wheel_with_no_bundled_libddwaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The guard must not fire on a wheel that legitimately has nothing to strip, otherwise it
    # would break the moment ddtrace stops vendoring the dylib itself.
    source_built_dir, source_external_dir, built_dir, external_dir = _repair_dirs(tmp_path)
    wheel_path = source_built_dir / 'ddtrace-1.0.0-cp313-cp313-macosx_12_0_arm64.whl'
    write_wheel(wheel_path, dylib_path=None)
    _stub_delocate(monkeypatch)

    repair_wheels.repair_darwin(
        str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
    )

    assert (built_dir / wheel_path.name).exists()
