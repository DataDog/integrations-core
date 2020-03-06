# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import contextlib
from typing import Any, Generic, Iterator, List, Type, TypeVar

import mock

from datadog_checks.snmp import utils

T = TypeVar("T")


@contextlib.contextmanager
def mock_profiles_root(root):
    # type: (str) -> Iterator[None]
    with mock.patch.object(utils, '_get_profiles_root', return_value=root):
        yield


class ClassInstantiationSpy(Generic[T]):
    """
    Record instantiations of a class.
    """

    def __init__(self, cls):
        # type: (Type[T]) -> None
        self.cls = cls
        self.calls = []  # type: List[tuple]

    def __call__(self, *args):
        # type: (*Any) -> T
        self.calls.append(args)
        return self.cls(*args)

    def assert_called_once_with(self, *args):
        # type: (*Any) -> None
        assert self.calls.count(args) == 1

    def assert_any_call(self, *args):
        # type: (*Any) -> None
        assert args in self.calls

    def reset(self):
        # type: () -> None
        self.calls.clear()
