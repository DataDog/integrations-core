from __future__ import annotations

import csv
import json
from collections import defaultdict
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, RootModel, computed_field

from ddev.cli.application import Application
from ddev.utils.fs import Path

TotalsDict = defaultdict[str, defaultdict[str, int]]


class Size(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="Name")
    version: str = Field(alias="Version")
    size_bytes: int = Field(alias="Size_Bytes")
    type: str = Field(alias="Type")
    platform: str = Field(alias="Platform")
    python_version: str = Field(alias="Python_Version")
    delta_type: str | None = Field(alias="Delta_Type", default=None, description="optional")
    percentage: float | None = Field(alias="Percentage", default=None, description="optional")

    @computed_field
    def size(self) -> str:
        if self.delta_type is not None and self.percentage is not None and self.size_bytes > 0:
            return "+" + convert_to_human_readable_size(self.size_bytes)
        return convert_to_human_readable_size(self.size_bytes)


class Sizes(RootModel[list[Size]]):
    _total_sizes: TotalsDict = PrivateAttr(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    _platforms: set[str] = PrivateAttr(default_factory=set)
    _python_versions: set[str] = PrivateAttr(default_factory=set)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for size_item in self.root:
            self._total_sizes[size_item.platform][size_item.python_version] += size_item.size_bytes
            self._platforms.add(size_item.platform)
            self._python_versions.add(size_item.python_version)

    def filter(
        self,
        platform: str | None = None,
        python_version: str | None = None,
        type: str | None = None,
        name: str | None = None,
        version: str | None = None,
        delta_type: str | None = None,
    ) -> Sizes:
        all_args = locals()

        filter_keys = ["platform", "python_version", "type", "name", "version", "delta_type"]

        active_filters = {key: all_args[key] for key in filter_keys if all_args[key] is not None}

        if not active_filters:
            return Sizes(self.root)

        return Sizes(
            [size for size in self.root if all(getattr(size, key) == value for key, value in active_filters.items())]
        )

    def get_size(self, platform: str, python_version: str, type: str, name: str) -> Size | None:
        return next(
            (
                size
                for size in self.root
                if (
                    size.platform == platform
                    and size.python_version == python_version
                    and size.type == type
                    and size.name == name
                )
            ),
            None,
        )

    def get_dictionary(self) -> dict[tuple[str, str, str, str], Size]:
        return {(size.name, size.type, size.platform, size.python_version): size for size in self.root}

    def append(self, size: Size) -> None:
        self.root.append(size)

        self._total_sizes[size.platform][size.python_version] += size.size_bytes
        self._platforms.add(size.platform)
        self._python_versions.add(size.python_version)

    def diff(self, other: "Sizes") -> "Sizes":
        result: "Sizes" = Sizes([])

        self_dict = self.get_dictionary()
        other_dict = other.get_dictionary()
        all_keys = set(self_dict) | set(other_dict)

        for name, type, platform, python_version in all_keys:
            self_size = self_dict.get((name, type, platform, python_version))
            other_size = other_dict.get((name, type, platform, python_version))

            self_size_bytes = self_size.size_bytes if self_size else 0
            other_size_bytes = other_size.size_bytes if other_size else 0

            delta = self_size_bytes - other_size_bytes
            percentage = (delta / other_size_bytes) * 100 if other_size_bytes != 0 else 0.0

            self_version = self_size.version if self_size else ""
            other_version = other_size.version if other_size else ""

            if other_size_bytes == 0:
                delta_type = "New"
                version = self_version
            elif self_size_bytes == 0:
                delta_type = "Removed"
                version = other_version
            elif delta != 0:
                delta_type = "Modified"
                version = f"{other_version} -> {self_version}" if self_version != other_version else self_version
            else:
                delta_type = "Unchanged"
                version = self_version

            result.append(
                Size(
                    name=name,
                    version=version,
                    size_bytes=delta,
                    type=type,
                    platform=platform,
                    python_version=python_version,
                    delta_type=delta_type,
                    percentage=round(percentage, 2),
                )
            )
        return result

    def __add__(self, other: "Sizes") -> "Sizes":
        return Sizes(self.root + other.root)

    def __len__(self) -> int:
        return len(self.root)

    def len_non_zero(self) -> int:
        return sum(1 for size in self.root if size.size_bytes != 0)

    def filter_no_zero(self) -> "Sizes":
        return Sizes([size for size in self.root if size.size_bytes != 0])

    def sort(self, key: Callable[[Size], Any] | None = None, reverse: bool = True) -> None:
        def default_key(size: Size) -> int:
            return abs(size.size_bytes)

        self.root.sort(key=key or default_key, reverse=reverse)

    def export_to_json(self, app: Application, file_path: Path, by_alias: bool = False) -> None:
        data = self.model_dump(by_alias=by_alias, exclude_none=True)
        if not data:
            app.display_warning("No data to export")
            return
        with file_path.open(mode="w", encoding="utf-8") as f:
            json.dump(data, f, default=str, indent=2)
        app.display(f"JSON file saved to {file_path}")

    def export_to_csv(self, app: Application, file_path: Path, by_alias: bool = False) -> None:
        data = self.model_dump(by_alias=by_alias, exclude_none=True)
        if not data:
            app.display_warning("No data to export")
            return
        with file_path.open(mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        app.display(f"CSV file saved to {file_path}")

    def export_to_markdown(self, app: Application, file_path: Path, by_alias: bool = False) -> None:
        if not self.root:
            app.display_warning("No data to export")
            return

        has_delta = any(s.delta_type is not None for s in self.root)
        has_percentage = any(s.percentage is not None for s in self.root)

        all_headers = list(Size.model_fields.keys()) + list(Size.model_computed_fields.keys())
        headers = [
            field
            for field in all_headers
            if "bytes" not in field
            and (has_delta or "delta_type" not in field)
            and (has_percentage or "percentage" not in field)
        ]

        lines = []

        for platform in self._platforms:
            for python_version in self._python_versions:
                sizes = self.filter(platform=platform, python_version=python_version)
                if sizes:
                    lines.append(f"## Platform: {platform}, Python Version: {python_version}")
                    lines.append("")
                    lines.append("| " + " | ".join(headers) + " |")
                    lines.append("| " + " | ".join("---" for _ in headers) + " |")
                    for size in sizes.root:
                        lines.append("| " + " | ".join(str(getattr(size, h, "")) for h in headers) + " |")
                    lines.append("")

        markdown = "\n".join(lines)
        with file_path.open(mode="w", encoding="utf-8") as f:
            f.write(markdown)
        app.display(f"Markdown file saved to {file_path}")

    def print_table(self, app: Application, title: str = "Sizes") -> None:
        if not self.root:
            app.display_warning("No data to display")
            return

        has_delta = any(s.delta_type is not None for s in self.root)
        has_percentage = any(s.percentage is not None for s in self.root)

        all_headers = list(Size.model_fields.keys()) + list(Size.model_computed_fields.keys())
        columns = [
            field
            for field in all_headers
            if "bytes" not in field
            and (has_delta or "delta_type" not in field)
            and (has_percentage or "percentage" not in field)
        ]

        modules_table: dict[str, dict[int, str]] = {col: {} for col in columns}
        for i, row in enumerate(self.root):
            if row.size_bytes == 0:
                continue
            for key in columns:
                modules_table[key][i] = str(getattr(row, key, ""))

        app.display_table(title, modules_table)


def convert_to_human_readable_size(size_bytes: float) -> str:
    size = abs(size_bytes)
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if size < 1024:
            return f"{size:0.2f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:0.2f} TiB"
