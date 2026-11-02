# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import math
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from .constants import PARSE_ERROR_CODE
from .errors import PanosApiError


def parse_response(body: bytes) -> Element:
    """Return the root `<response>`; raise PanosApiError for an error response or a body that is not PAN-OS XML."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        raise PanosApiError(PARSE_ERROR_CODE, f'response is not valid XML: {e}', panos_response=False) from e
    return check_response(root)


def check_response(root: Element) -> Element:
    """The tag check rejects well-formed XML that is not from PAN-OS, such as a proxy's XHTML error page."""
    if root.tag != 'response':
        raise PanosApiError(
            PARSE_ERROR_CODE, f'unexpected root element <{root.tag}>, expected <response>', panos_response=False
        )
    if root.get('status') == 'error':
        msg = ' '.join(t.strip() for m in root.iter('msg') for t in m.itertext() if t.strip())
        raise PanosApiError(root.get('code') or '', msg)
    return root


def text(elem: Element | None, path: str, default: str | None = None) -> str | None:
    """The stripped text at `path`, or `default` if absent or empty."""
    if elem is None:
        return default
    value = elem.findtext(path)
    if value is None or not value.strip():
        return default
    return value.strip()


def num(elem: Element | None, path: str, default: float | None = None) -> float | None:
    """The text at `path` as a float; `default` if missing, unparseable or not finite."""
    value = text(elem, path)
    if value is None:
        return default
    try:
        result = float(value)
    except ValueError:
        return default
    return result if math.isfinite(result) else default


def tag_tuple(*pairs: tuple[str, str | None]) -> tuple[str, ...]:
    return tuple(f'{name}:{value}' for name, value in pairs if value)
