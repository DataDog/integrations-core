# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any

from openstack import exceptions as openstack_exceptions

from datadog_checks.base.utils.http_exceptions import HTTPStatusError


class OpenStackSDKError(Exception):
    pass


class OpenStackHTTPResponse:
    def __init__(self, response: Any = None, status_code: int | None = None) -> None:
        self.status_code = status_code if status_code is not None else getattr(response, 'status_code', None)
        self.headers = dict(getattr(response, 'headers', {}) or {})
        self.content = getattr(response, 'content', b'') or b''
        self.text = getattr(response, 'text', '') or ''
        self.encoding = getattr(response, 'encoding', None)
        self.elapsed = getattr(response, 'elapsed', timedelta())
        self.cookies = getattr(response, 'cookies', {}) or {}
        self.links = getattr(response, 'links', {}) or {}
        self.url = getattr(response, 'url', '') or ''
        self.history = list(getattr(response, 'history', []) or [])
        self.reason = getattr(response, 'reason', '') or ''

    @property
    def ok(self) -> bool:
        return self.status_code is not None and self.status_code < 400

    def json(self, **kwargs: Any) -> Any:
        return json.loads(self.text, **kwargs)

    def raise_for_status(self) -> None:
        if self.status_code is not None and self.status_code >= 400:
            raise HTTPStatusError(str(self), response=self)

    def close(self) -> None:
        pass


def http_status_code(error: BaseException, response: Any = None) -> int | None:
    error_response = getattr(error, 'response', None) or response
    status_code = getattr(error_response, 'status_code', None)
    if status_code is not None:
        return status_code
    return getattr(error, 'status_code', None)


def openstack_http_response(error: openstack_exceptions.HttpException) -> OpenStackHTTPResponse | None:
    status_code = http_status_code(error)
    if status_code is None:
        return None
    return OpenStackHTTPResponse(getattr(error, 'response', None), status_code=status_code)


def translate_openstack_error(error: BaseException) -> BaseException:
    if isinstance(error, openstack_exceptions.HttpException):
        return HTTPStatusError(str(error), response=openstack_http_response(error))
    if isinstance(error, openstack_exceptions.SDKException):
        return OpenStackSDKError(str(error))
    return error


def translate_openstack_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except openstack_exceptions.SDKException as error:
            raise translate_openstack_error(error) from error

    return wrapper


def translate_openstack_sdk_methods(cls: type) -> type:
    for name, value in vars(cls).items():
        if name.startswith('_') or not callable(value):
            continue
        setattr(cls, name, translate_openstack_errors(value))
    return cls
