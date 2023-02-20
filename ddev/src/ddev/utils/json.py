# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from jsonpointer import resolve_pointer, set_pointer

if TYPE_CHECKING:
    from ddev.utils.fs import Path


class JSONPointer:
    def __init__(self, data: dict):
        self.__data = data

    @property
    def data(self) -> dict:
        return self.__data

    def get(self, *args, **kwargs):
        return resolve_pointer(self.__data, *args, **kwargs)

    def set(self, *args, **kwargs):
        return set_pointer(self.__data, *args, **kwargs)


class JSONPointerFile:
    def __init__(self, path: Path):
        self.__path = path

    @property
    def path(self) -> Path:
        return self.__path

    def get(self, *args, **kwargs):
        return self.__jsonpointer.get(*args, **kwargs)

    def set(self, *args, **kwargs):
        return self.__jsonpointer.set(*args, **kwargs)

    def save(self):
        self.save_data(self.__jsonpointer.data)

    def load_data(self) -> dict:
        import json

        return json.loads(self.path.read_text())

    def save_data(self, data: dict):
        import json

        self.path.write_text(json.dumps(data, indent=4))

    @cached_property
    def __jsonpointer(self) -> JSONPointer:
        if not self.path.is_file():
            return JSONPointer({})

        return JSONPointer(self.load_data())
