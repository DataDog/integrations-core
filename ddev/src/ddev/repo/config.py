# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import tomllib
from typing import Any

from ddev.utils.fs import Path
from ddev.utils.json import JSONPointerFile

IMPORTS_KEY = 'imports'


class RepositoryConfigError(ValueError):
    """Raised for invalid repository configuration files, e.g. bad `imports` declarations or conflicting keys."""


class RepositoryConfig(JSONPointerFile):
    """
    Represents a `/.ddev/config.toml` file.

    The file may declare a top-level `imports` key: a list of TOML file paths relative to the config's
    directory (e.g. `.ddev/config.toml` importing `dispatcher.toml` from `.ddev/dispatcher.toml`). Each
    imported file is parsed independently, and each top-level key must be defined in exactly one file, so
    every file owns whole tables. A file listed more than once is loaded once. The `imports` key itself is
    not part of the loaded data.
    """

    def load_data(self) -> dict:
        data = _load_config_file(self.path)
        imports = data.pop(IMPORTS_KEY, None)
        if imports is None:
            return data

        if not isinstance(imports, list) or not all(isinstance(entry, str) for entry in imports):
            raise RepositoryConfigError(f'`{IMPORTS_KEY}` in {self.path} must be a list of file names')

        sources = dict.fromkeys(data, self.path)
        seen: set[Path] = set()
        for entry in imports:
            imported_path = self._resolve_import(entry)
            if imported_path in seen:
                continue
            seen.add(imported_path)

            imported_data = _load_config_file(imported_path)
            # Nested imports are intentionally unsupported: nothing needs them yet.
            if IMPORTS_KEY in imported_data:
                raise RepositoryConfigError(
                    f'{imported_path} declares `{IMPORTS_KEY}`, but nested imports are not supported'
                )
            for key, value in imported_data.items():
                if key in sources:
                    raise RepositoryConfigError(f'`{key}` is defined in both {sources[key]} and {imported_path}')
                data[key] = value
                sources[key] = imported_path

        return data

    def save_data(self, data: dict):
        import tomli_w

        if self.path.is_file() and IMPORTS_KEY in _load_config_file(self.path):
            raise RepositoryConfigError(
                f'Refusing to save {self.path}: it declares `{IMPORTS_KEY}`, and writing the merged data back '
                'would flatten the split into a single file'
            )

        self.path.write_text(tomli_w.dumps(data))

    def _resolve_import(self, entry: str) -> Path:
        config_dir = self.path.parent.resolve()

        import_path = Path(entry)
        if import_path.is_absolute():
            raise RepositoryConfigError(f'`{IMPORTS_KEY}` entry in {self.path} must be relative, not absolute: {entry}')

        resolved = (config_dir / import_path).resolve()
        # The Dispatcher planner reads this config from arbitrary pull requests, so an import must never
        # be able to point at files outside the config's directory.
        if not resolved.is_relative_to(config_dir):
            raise RepositoryConfigError(f'`{IMPORTS_KEY}` entry in {self.path} escapes the config directory: {entry}')
        if resolved == self.path.resolve():
            raise RepositoryConfigError(f'`{IMPORTS_KEY}` entry in {self.path} imports the file itself: {entry}')
        if not resolved.exists():
            raise RepositoryConfigError(f'`{IMPORTS_KEY}` entry in {self.path} does not exist: {entry}')
        if not resolved.is_file():
            raise RepositoryConfigError(f'`{IMPORTS_KEY}` entry in {self.path} is not a file: {entry}')

        return resolved


def _load_config_file(path: Path) -> dict[str, Any]:
    """Parse one configuration file, naming it in the error since a configuration can span several."""
    try:
        return tomllib.loads(path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as error:
        raise RepositoryConfigError(f'{path} is not valid TOML: {error}') from error
