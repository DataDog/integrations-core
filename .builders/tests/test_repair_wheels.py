import base64
import csv
import hashlib
import importlib
import io
import shutil
import struct
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


CPU_TYPE_ARM64 = 0x0100000C
CPU_TYPE_X86_64 = 0x01000007
# x86_64 executables carry this capability flag in their cpusubtype
CPU_SUBTYPE_LIB64 = 0x80000000
ARM64_SLICE = b'\xcf\xfa\xed\xfe arm64 slice'
X86_64_SLICE = b'\xcf\xfa\xed\xfe x86_64 slice'
SLICES = {'arm64': ARM64_SLICE, 'x86_64': X86_64_SLICE}


def universal_binary(slices: list[tuple[int, int, bytes]], fat64: bool = False) -> bytes:
    """Build a universal Mach-O binary from `(cputype, cpusubtype, contents)` slices, each aligned to 64 bytes."""
    magic, arch_format = (0xCAFEBABF, '>IIQQII') if fat64 else (0xCAFEBABE, '>IIIII')
    header = struct.pack('>II', magic, len(slices))
    entries = b''
    body = b''
    offset = 8 + len(slices) * struct.calcsize(arch_format)
    for cputype, cpusubtype, contents in slices:
        padding = -offset % 64
        offset += padding
        fields = (cputype, cpusubtype, offset, len(contents), 6) + ((0,) if fat64 else ())
        entries += struct.pack(arch_format, *fields)
        body += b'\0' * padding + contents
        offset += len(contents)
    return header + entries + body


UNIVERSAL_SLICES = [(CPU_TYPE_X86_64, CPU_SUBTYPE_LIB64 | 3, X86_64_SLICE), (CPU_TYPE_ARM64, 0, ARM64_SLICE)]


def record_hash(contents: bytes) -> str:
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b'=').decode('ascii')


def write_wheel_with_record(path: Path, members: dict[str, bytes]) -> None:
    record_path = f'{path.name.split("-")[0]}-{path.name.split("-")[1]}.dist-info/RECORD'
    record = io.StringIO(newline='')
    writer = csv.writer(record, lineterminator='\n')
    for name, contents in members.items():
        writer.writerow((name, record_hash(contents), str(len(contents))))
    writer.writerow((record_path, '', ''))

    with ZipFile(path, 'w') as wheel:
        for name, contents in members.items():
            info = ZipInfo(name, date_time=(2024, 1, 2, 3, 4, 6))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o755 << 16
            wheel.writestr(info, contents)
        wheel.writestr(record_path, record.getvalue())


@pytest.mark.parametrize('fat64', [False, True], ids=['fat', 'fat64'])
@pytest.mark.parametrize('arch', ['arm64', 'x86_64'])
def test_thin_universal_binary_returns_the_slice_of_the_arch(arch: str, fat64: bool):
    binary = universal_binary(UNIVERSAL_SLICES, fat64=fat64)

    assert repair_wheels._thin_universal_binary(binary, arch) == SLICES[arch]


def test_thin_universal_binary_without_a_slice_for_the_arch_raises():
    binary = universal_binary([(CPU_TYPE_X86_64, 3, X86_64_SLICE)])

    with pytest.raises(ValueError, match='no arm64 slice'):
        repair_wheels._thin_universal_binary(binary, 'arm64')


@pytest.mark.parametrize(
    'contents',
    [
        pytest.param(ARM64_SLICE, id='thin-macho'),
        # Java class files start with the same magic, followed by their version (here Java 21)
        pytest.param(struct.pack('>IHH', 0xCAFEBABE, 0, 65) + b'class body', id='java-class'),
        pytest.param(b'\xca\xfe', id='truncated'),
    ],
)
def test_thin_universal_binary_leaves_other_files_alone(contents: bytes):
    assert repair_wheels._thin_universal_binary(contents, 'arm64') is None


@pytest.mark.parametrize('arch', ['arm64', 'x86_64'])
def test_repair_darwin_thins_universal_external_wheel_into_built_wheel_for_host_arch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arch: str
):
    source_built_dir = tmp_path / 'source-built'
    source_external_dir = tmp_path / 'source-external'
    built_dir = tmp_path / 'built'
    external_dir = tmp_path / 'external'
    for directory in (source_built_dir, source_external_dir, built_dir, external_dir):
        directory.mkdir()

    # PyPI's universal orjson wheel, whose compressed tag set covers both architectures
    wheel_path = (
        source_external_dir
        / 'orjson-3.13.0-cp313-cp313-macosx_10_15_x86_64.macosx_11_0_arm64.macosx_10_15_universal2.whl'
    )
    extension_path = 'orjson/orjson.cpython-313-darwin.so'
    wheel_metadata_path = 'orjson-3.13.0.dist-info/WHEEL'
    write_wheel_with_record(
        wheel_path,
        {
            'orjson/__init__.py': b'from .orjson import *\n',
            extension_path: universal_binary(UNIVERSAL_SLICES),
            wheel_metadata_path: (
                b'Wheel-Version: 1.0\n'
                b'Generator: maturin (1.9.6)\n'
                b'Root-Is-Purelib: false\n'
                b'Tag: cp313-cp313-macosx_10_15_x86_64\n'
                b'Tag: cp313-cp313-macosx_11_0_arm64\n'
                b'Tag: cp313-cp313-macosx_10_15_universal2\n'
            ),
        },
    )
    with ZipFile(wheel_path) as wheel:
        original_extension_info = wheel.getinfo(extension_path)

    # delocate is a macOS-only native tool that isn't under test here
    monkeypatch.setitem(sys.modules, 'delocate', SimpleNamespace(delocate_wheel=None))
    monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', '12.0')
    # The host CPU architecture is a platform boundary: pin it so the result doesn't depend on the machine
    monkeypatch.setattr(repair_wheels.os, 'uname', lambda: SimpleNamespace(machine=arch))

    repair_wheels.repair_darwin(
        str(source_built_dir), str(source_external_dir), str(built_dir), str(external_dir)
    )

    assert list(external_dir.iterdir()) == []
    assert [path.name for path in built_dir.iterdir()] == [f'orjson-3.13.0-cp313-cp313-macosx_12_0_{arch}.whl']
    with ZipFile(built_dir / f'orjson-3.13.0-cp313-cp313-macosx_12_0_{arch}.whl') as wheel:
        assert wheel.read(extension_path) == SLICES[arch]
        assert wheel.getinfo(extension_path).external_attr == original_extension_info.external_attr
        assert wheel.read(wheel_metadata_path).decode('utf-8') == (
            'Wheel-Version: 1.0\n'
            'Generator: maturin (1.9.6)\n'
            'Root-Is-Purelib: false\n'
            f'Tag: cp313-cp313-macosx_12_0_{arch}\n'
        )
        record = wheel.read('orjson-3.13.0.dist-info/RECORD').decode('utf-8')
        record_rows = list(csv.reader(io.StringIO(record, newline='')))
        assert {row[0] for row in record_rows} == set(wheel.namelist())
        for name, digest, size in record_rows:
            if digest:
                contents = wheel.read(name)
                assert (digest, size) == (record_hash(contents), str(len(contents))), name
