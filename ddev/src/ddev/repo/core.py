from __future__ import annotations

from ddev.utils.fs import Path


class Repository:
    def __init__(self, name: str, path: str):
        self.__name = name
        self.__path = Path(path)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> Path:
        return self.__path
