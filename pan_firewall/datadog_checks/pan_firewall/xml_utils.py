# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from .constants import PARSE_ERROR_CODE
from .errors import PanosApiError


def parse_response(body: bytes) -> Element:
    """Parse a PAN-OS XML API response and return its root `<response>` element.

    Raises PanosApiError for `status="error"` responses and for bodies that are not XML.
    """
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        raise PanosApiError(PARSE_ERROR_CODE, f'response is not valid XML: {e}') from e

    if root.get('status') == 'error':
        msg = ' '.join(t.strip() for m in root.iter('msg') for t in m.itertext() if t.strip())
        raise PanosApiError(root.get('code') or '', msg)
    return root


def text(elem: Element | None, path: str, default: str | None = None) -> str | None:
    """Return the stripped text of the first element matching `path`, or `default` if absent or empty."""
    if elem is None:
        return default
    value = elem.findtext(path)
    if value is None or not value.strip():
        return default
    return value.strip()


def num(elem: Element | None, path: str, default: float | None = None) -> float | None:
    """Return the text at `path` as a float. Never raises: missing or unparseable values give `default`."""
    value = text(elem, path)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default
