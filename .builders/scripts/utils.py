from pathlib import Path
from typing import Iterator


def iter_wheels(source_dir: str) -> Iterator[Path]:
    for entry in sorted(Path(source_dir).iterdir(), key=lambda entry: entry.name.casefold()):
        if entry.suffix == '.whl' and entry.is_file():
            yield entry
