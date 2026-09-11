# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from dataclasses import dataclass

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ObfuscationResult:
    obfuscated_query: str
    query_signature: str
    tables: list[str] | None
    commands: list[str] | None
    comments: list[str] | None


def obfuscate_statement(
    raw_text: str, obfuscate_options: str, log_unobfuscated_queries: bool = False
) -> ObfuscationResult | None:
    """Obfuscate one statement via the FFI, returning None if it cannot be obfuscated.

    Exposed separately from :class:`~.cache.ObfuscationLookup` for statement sources whose identity
    does not determine their text, which therefore cannot be cached. MySQL's
    ``prepared_statements_instances`` is one: it is keyed on a reusable memory address, so a
    recycled instance can carry unrelated text and every row has to be obfuscated afresh.
    """
    try:
        statement = obfuscate_sql_with_metadata(raw_text, obfuscate_options)
    except Exception as e:
        if log_unobfuscated_queries:
            logger.warning("Failed to obfuscate query=[%s] | err=[%s]", raw_text, e)
        else:
            logger.debug("Failed to obfuscate query | err=[%s]", e)
        return None

    obfuscated_query = statement['query']
    metadata = statement['metadata']
    return ObfuscationResult(
        obfuscated_query=obfuscated_query,
        query_signature=compute_sql_signature(obfuscated_query),
        tables=metadata.get('tables', None),
        commands=metadata.get('commands', None),
        comments=metadata.get('comments', None),
    )
