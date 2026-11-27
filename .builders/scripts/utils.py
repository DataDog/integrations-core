from pathlib import Path
from typing import Iterator

from packaging.tags import mac_platforms
from packaging.utils import parse_wheel_filename


def iter_wheels(source_dir: str | Path) -> Iterator[Path]:
    for entry in sorted(Path(source_dir).iterdir(), key=lambda entry: entry.name.casefold()):
        if entry.suffix == '.whl' and entry.is_file():
            yield entry


def wheel_supports_macos(wheel_name: str, macos_version: tuple[int, int], arch: str) -> bool:
    """Whether any platform tag of the wheel, including compressed tag sets, installs on `macos_version` for `arch`."""
    supported = {'any', *mac_platforms(macos_version, arch)}
    _, _, _, tags = parse_wheel_filename(wheel_name)
    return any(tag.platform in supported for tag in tags)
