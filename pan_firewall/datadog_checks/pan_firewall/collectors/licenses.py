# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Licenses and subscriptions (`request license info`): days until expiry and expired flag, per feature."""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.xml_utils import text

from . import CollectContext, Sample, once_log, register

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

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
    """The expiry date, or None for a perpetual license (`Never`) or a date in an unknown format."""
    match = EXPIRY_DATE.match(value)
    month = MONTHS.get(match['month'].lower()) if match else None
    if not match or not month:
        return None
    try:
        return datetime.date(int(match['year']), month, int(match['day']))
    except ValueError:
        return None


def parse_licenses(root: Element, log: CheckLoggingAdapter, today: datetime.date) -> list[Sample]:
    """One `license.expired` per feature, and `license.days_left` when `expires` is a date.

    A perpetual license (`Never`) or an unparseable date reports `expired` only: no day count is made up.
    """
    licenses = root.find('result/licenses')
    if licenses is None:
        log.warning('Unknown shape of `request license info`: no result/licenses, sending no license metrics')
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
            log.debug('License %s has an unparseable expiry date %r', feature, expires)
        expired = (text(entry, 'expired') or '').lower()
        if expired in ('yes', 'no'):
            samples.append(Sample('license.expired', int(expired == 'yes'), tags, 'gauge'))
    return samples


@register('licenses')
def collect_licenses(ctx: CollectContext, today: datetime.date | None = None) -> list[Sample]:
    return parse_licenses(ctx.client.op(LICENSE_INFO_CMD), once_log(ctx), today or datetime.date.today())
