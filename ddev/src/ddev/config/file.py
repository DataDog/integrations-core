# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ddev.config.model import RootConfig
from ddev.config.utils import scrub_config
from ddev.utils.fs import Path
from ddev.utils.toml import dumps_toml_data, load_toml_data

LOCAL_OVERRIDES_PATH = Path.cwd() / ".ddev.toml"
UNINITIALIZED = object()


class ConfigFileError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def deep_merge_with_list_handling(left: dict, right: dict) -> dict:
    """Merge two dictionaries, by adding/replacing values from the right dictionary on to the left one
    handling lists by concatenating them and recursively merging nested dictionaries.

    This function is optimized for TOML data structures, which only contain:
    - Simple immutable types (strings, numbers, booleans, dates)
    - Lists (arrays)
    - Dictionaries (tables)

    Example:
        >>> a = {"a": 1, "b": 2, "c": {"d": [1, 2, 3], "e": 5}, "f": [1, 2, 3]}
        >>> b = {"c": {"d": [7, 8]}, "f": [6], "b": "x"}
        >>> deep_merge_with_list_handling(a, b)
        {"a": 1, "b": "x", "c": {"d": [1, 2, 3, 7, 8], "e": 5}, "f": [1, 2, 3, 6]}
    """
    result = dict(left)  # Shallow copy is sufficient for the top level
    for key, value in right.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = deep_merge_with_list_handling(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # Create a new list for concatenation
                result[key] = result[key][:] + value[:]
            else:
                # For non-dict, non-list values (immutable in TOML), direct assignment is safe
                result[key] = value
        else:
            if isinstance(value, dict):
                # Copy dictionary to avoid modifying the original
                result[key] = dict(value)
            elif isinstance(value, list):
                # Copy list to avoid modifying the original
                result[key] = value[:]
            else:
                # For immutable types, direct assignment is safe
                result[key] = value
    return result


def build_line_index_with_multiple_entries(content: str) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped_line = line.strip()
        index.setdefault(stripped_line, []).append(line_number)
    return index


@dataclass
class ProcessedConfigs:
    combined_lines: list[str]
    line_sources: dict[int, str] | None
    combined_content: str
    global_content: str
    local_content: str


class ConfigFileWithOverrides:
    """
    A ConfigFile that combines the global config with the local overrides.
    """

    def __init__(self, path: Path | None = None):
        self.global_path = path or ConfigFileWithOverrides.get_default_location()
        self.global_model: RootConfig = cast(RootConfig, UNINITIALIZED)
        self.global_content: str = ""
        self.local_model: RootConfig = cast(RootConfig, UNINITIALIZED)
        self.local_content: str = ""
        self.combined_model: RootConfig = cast(RootConfig, UNINITIALIZED)
        self.combined_content: str = ""

    @property
    def local_path(self) -> Path:
        return LOCAL_OVERRIDES_PATH

    def overrides_available(self) -> bool:
        return self.local_path.is_file()

    def load(self):
        self.global_content = self.global_path.read_text()
        self.global_model = RootConfig(load_toml_data(self.global_content))

        if not self.overrides_available() or (local_content := self.local_path.read_text()).strip() == "":
            self.combined_model = self.global_model
            self.combined_content = dumps_toml_data(self.combined_model.raw_data)
            self.local_content = ""
            self.local_model = RootConfig({})
            return

        self.local_content = local_content
        self.local_model = RootConfig(load_toml_data(self.local_content))

        self.combined_model = RootConfig(
            deep_merge_with_list_handling(
                cast(RootConfig, self.global_model).raw_data,
                self.local_model.raw_data,
            )
        )
        self.combined_content = dumps_toml_data(self.combined_model.raw_data)

    def _process_combined_configs(self, scrubbed: bool) -> ProcessedConfigs:
        if self.combined_model is UNINITIALIZED:
            raise ConfigFileError("Config file not loaded")

        if scrubbed:
            scrub_config(cast(RootConfig, self.combined_model).raw_data)
            combined_content = dumps_toml_data(cast(RootConfig, self.combined_model).raw_data)
            combined_lines = combined_content.splitlines()
            scrub_config(cast(RootConfig, self.global_model).raw_data)
            global_content = dumps_toml_data(cast(RootConfig, self.global_model).raw_data)
            scrub_config(cast(RootConfig, self.local_model).raw_data)
            local_content = dumps_toml_data(cast(RootConfig, self.local_model).raw_data)
        else:
            combined_lines = self.combined_content.splitlines()
            combined_content = self.combined_content
            global_content = self.global_content
            local_content = self.local_content

        global_index = build_line_index_with_multiple_entries(global_content)
        local_index = build_line_index_with_multiple_entries(local_content)

        # If we have no local content, there is no need to build the line sources
        if not local_content:
            return ProcessedConfigs(
                combined_lines=combined_lines,
                line_sources=None,
                combined_content=combined_content,
                global_content=global_content,
                local_content=local_content,
            )

        line_sources = {}
        # Use SequenceMatcher to find matching lines and their sources
        for line_number, line in enumerate(combined_lines):
            stripped_line = line.strip()

            if not stripped_line:  # Skip empty lines
                continue

            try:
                # Check if this line exists in local config
                if stripped_line in local_index:
                    line_sources[line_number] = f"{self.local_path.name}:{local_index[stripped_line].pop(0)}"
                # If not found in local, it must be from global
                elif stripped_line in global_index:
                    line_sources[line_number] = f"{self.global_path.name}:{global_index[stripped_line].pop(0)}"
                else:
                    # If it is not in global there has been some unexpected error when parsing the configs
                    return ProcessedConfigs(
                        combined_lines=combined_lines,
                        line_sources=None,
                        combined_content=combined_content,
                        global_content=global_content,
                        local_content=local_content,
                    )
            except KeyError:
                # Pop will throw key error if there are no more elements in the list
                return ProcessedConfigs(
                    combined_lines=combined_lines,
                    line_sources=None,
                    combined_content=combined_content,
                    global_content=global_content,
                    local_content=local_content,
                )

        return ProcessedConfigs(
            combined_lines=combined_lines,
            line_sources=line_sources,
            combined_content=combined_content,
            global_content=global_content,
            local_content=local_content,
        )

    def _build_read_string(self, lines: list[str], line_sources: dict[int, str]) -> str:
        """Build the annotated output."""
        max_line_length = max(len(line.strip()) for line in lines)

        annotated_lines = []
        for line_number, line in enumerate(lines):
            if not line.strip():  # Skip empty lines
                annotated_lines.append(line)
                continue

            source = line_sources.get(line_number, self.global_path.name)
            annotated_lines.append(f"{line:<{max_line_length}}  # {source}")

        return "\n".join(annotated_lines)

    def _read(self, scrubbed: bool) -> str:
        result = self._process_combined_configs(scrubbed)

        if result.line_sources is None:
            return result.combined_content

        return self._build_read_string(result.combined_lines, result.line_sources)

    def read(self) -> str:
        """Read the combined configuration with source annotations."""
        return self._read(False)

    def read_scrubbed(self) -> str:
        """Read the combined configuration with source annotations, with sensitive data scrubbed."""
        return self._read(True)

    @property
    def path(self) -> Path:
        return self.global_path

    @path.setter
    def path(self, value: Path):
        self.global_path = value

    @property
    def model(self) -> RootConfig:
        return cast(RootConfig, self.global_model)

    def save(self, content=None):
        import tomli_w

        if not content:
            content = tomli_w.dumps(self.global_model.raw_data)

        self.global_path.ensure_parent_dir_exists()
        self.global_path.write_atomic(content, "w", encoding="utf-8")

    def reset(self):
        global_config = RootConfig({})
        global_config.parse_fields()
        combined_config = RootConfig({})
        combined_config.parse_fields()
        self.global_model = global_config
        self.combined_model = combined_config
        self.local_model = cast(RootConfig, UNINITIALIZED)
        self.local_content = ""

    def restore(self):
        import tomli_w

        self.reset()
        content = tomli_w.dumps(self.global_model.raw_data)
        self.save(content)

    def update(self):  # no cov
        self.global_model.parse_fields()
        self.save()

    @classmethod
    def get_default_location(cls) -> Path:
        from platformdirs import user_data_dir

        return Path(user_data_dir('dd-checks-dev', appauthor=False)) / 'config.toml'
