# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Licenses and subscriptions (`request license info`): days until expiry and expired flag, per feature."""

from __future__ import annotations

import datetime
import re
from collections.abc import Callable
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import text

from .base import CollectContext, Sample

LICENSE_INFO_CMD = '<request><license><info/></license></request>'

# `expires` reads `October 22, 2026`. Parsed by hand: `strptime('%B')` follows the process locale.
MONTH_NAMES: tuple[str, ...] = ('january', 'february', 'march', 'april', 'may', 'june')
MONTH_NAMES += ('july', 'august', 'september', 'october', 'november', 'december')
MONTHS = {name: number for number, name in enumerate(MONTH_NAMES, start=1)}
EXPIRY_DATE = re.compile(r'^(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),\s*(?P<year>\d{4})$')
NON_ALNUM = re.compile(r'[^a-z0-9]+')


def feature_tag(feature: str) -> str:
    """`PAN-DB URL Filtering` -> `pan_db_url_filtering`."""
    return NON_ALNUM.sub('_', feature.lower()).strip('_')


def parse_expiry(value: str) -> datetime.date | None:
    match = EXPIRY_DATE.match(value)
    month = MONTHS.get(match['month'].lower()) if match else None
    if not match or not month:
        return None
    try:
        return datetime.date(int(match['year']), month, int(match['day']))
    except ValueError:
        return None


def parse_licenses(
    root: Element, warn: Callable[..., None], debug: Callable[..., None], today: datetime.date
) -> list[Sample]:
    """A perpetual license (`Never`) or an unparseable date reports `expired` only: no day count is made up."""
    licenses = root.find('result/licenses')
    if licenses is None:
        warn('Unknown shape of `request license info`: no result/licenses, sending no license metrics')
        return []

    samples: list[Sample] = []
    for entry in licenses.iterfind('entry'):
        feature = text(entry, 'feature')
        if not feature:
            continue
        tags = (f'feature:{feature_tag(feature)}',)
        expires = text(entry, 'expires') or ''
        expiry = parse_expiry(expires)
        if expiry is not None:
            samples.append(Sample('license.days_left', (expiry - today).days, tags, 'gauge'))
        elif expires.lower() != 'never':
            debug('License %s has an unparseable expiry date %r', feature, expires)
        expired = (text(entry, 'expired') or '').lower()
        if expired in ('yes', 'no'):
            samples.append(Sample('license.expired', int(expired == 'yes'), tags, 'gauge'))
    return samples


def collect_licenses(ctx: CollectContext, today: datetime.date | None = None) -> list[Sample]:
    return parse_licenses(ctx.client.op(LICENSE_INFO_CMD), ctx.warning, ctx.debug, today or datetime.date.today())
