# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from functools import cached_property


class RepositoryConfig:
    def __init__(self, data: dict):
        self.__data = data

    @property
    def data(self) -> dict:
        return self.__data

    @cached_property
    def overrides(self) -> dict:
        overrides = self.data.get('overrides', {})
        if not isinstance(overrides, dict):
            raise TypeError('Repository configuration `overrides` must be a table')

        return overrides

    @cached_property
    def display_name_overrides(self) -> dict:
        display_name_overrides = self.overrides.get('display-name', {})
        if not isinstance(display_name_overrides, dict):
            raise TypeError('Repository configuration `overrides.display-name` must be a table')

        return display_name_overrides
