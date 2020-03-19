# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from collections import OrderedDict
from typing import Iterator, List, Tuple

import pytest

from datadog_checks.rethinkdb.document_db.query import DocumentQuery

pytestmark = pytest.mark.unit


class MockLogger(logging.Logger):
    def trace(self, *args, **kwargs):  # type: ignore
        pass  # Called by queries.


def test_document_query():
    # type: () -> None
    """
    A realistic unit test demonstrating the usage of `DocumentQuery`.
    """

    PRODUCTS_COLLECTION = [
        # NOTE: use ordered dicts so that order of submitted metrics is deterministic on Python 2 too.
        OrderedDict(
            (
                ('name', 'T-Shirt'),
                ('category', 'clothing'),
                ('sales', {'sales_per_day': 100, 'sales_total': 10000}),
                ('locations', [{'name': 'London', 'stock': 1200}, {'name': 'Paris', 'stock': 700}]),
                ('total_sales_per_location', OrderedDict((('london', 2000), ('paris', 8000)))),
            ),
        ),
        OrderedDict(
            (
                ('name', 'Laptop'),
                ('category', 'high-tech'),
                ('sales', {'sales_per_day': 5, 'sales_total': 400}),
                ('locations', [{'name': 'New York', 'stock': 150}]),
                ('total_sales_per_location', {'new-york': 400}),
            )
        ),
    ]

    def get_data_from_db(conn):
        # type: (dict) -> Iterator[Tuple[dict, List[str]]]
        for product in PRODUCTS_COLLECTION:
            tags = ['category:{}'.format(product['category']), 'server:{}'.format(conn['server'])]
            yield product, tags

    query = DocumentQuery(
        source=get_data_from_db,
        name='test',
        prefix='products',
        # Metrics obtained from a nested JSON key lookup (aka path lookup).
        metrics=[
            {'type': 'gauge', 'path': 'sales.sales_per_day'},
            {'type': 'monotonic_count', 'path': 'sales.sales_total'},
            {'type': 'gauge', 'path': 'locations', 'modifier': 'total'},
        ],
        # Metrics for each object in an array, tagged by the index in the array.
        enumerations=[
            {'path': 'locations', 'index_tag': 'location_index', 'metrics': [{'type': 'gauge', 'path': 'stock'}]}
        ],
        # Metrics from the result of a groupby() operation (aggregation).
        groups=[{'path': 'total_sales_per_location', 'key_tag': 'location', 'value_metric_type': 'gauge'}],
    )

    conn = {'server': 'example'}
    metrics = list(query.run(conn, logger=MockLogger('test')))

    assert metrics == [
        # -- T-Shirt --
        # Metrics
        {
            'type': 'gauge',
            'name': 'products.sales.sales_per_day',
            'value': 100,
            'tags': ['category:clothing', 'server:example'],
        },
        {
            'type': 'monotonic_count',
            'name': 'products.sales.sales_total',
            'value': 10000,
            'tags': ['category:clothing', 'server:example'],
        },
        {'type': 'gauge', 'name': 'products.locations', 'value': 2, 'tags': ['category:clothing', 'server:example']},
        # Enumerations
        {
            'type': 'gauge',
            'name': 'products.locations.stock',
            'value': 1200,
            'tags': ['category:clothing', 'server:example', 'location_index:0'],
        },
        {
            'type': 'gauge',
            'name': 'products.locations.stock',
            'value': 700,
            'tags': ['category:clothing', 'server:example', 'location_index:1'],
        },
        # Groups
        {
            'type': 'gauge',
            'name': 'products.total_sales_per_location',
            'value': 2000,
            'tags': ['category:clothing', 'server:example', 'location:london'],
        },
        {
            'type': 'gauge',
            'name': 'products.total_sales_per_location',
            'value': 8000,
            'tags': ['category:clothing', 'server:example', 'location:paris'],
        },
        # -- Laptop --
        # Metrics
        {
            'type': 'gauge',
            'name': 'products.sales.sales_per_day',
            'value': 5,
            'tags': ['category:high-tech', 'server:example'],
        },
        {
            'type': 'monotonic_count',
            'name': 'products.sales.sales_total',
            'value': 400,
            'tags': ['category:high-tech', 'server:example'],
        },
        {'type': 'gauge', 'name': 'products.locations', 'value': 1, 'tags': ['category:high-tech', 'server:example']},
        # Enumerations
        {
            'type': 'gauge',
            'name': 'products.locations.stock',
            'value': 150,
            'tags': ['category:high-tech', 'server:example', 'location_index:0'],
        },
        # Groups
        {
            'type': 'gauge',
            'name': 'products.total_sales_per_location',
            'value': 400,
            'tags': ['category:high-tech', 'server:example', 'location:new-york'],
        },
    ]


def test_document_query_empty():
    # type: () -> None
    def get_data():
        # type: () -> Iterator[Tuple[dict, List[str]]]
        yield {}, []

    query = DocumentQuery(source=get_data, name='test', prefix='dogs')
    metrics = list(query.run(logger=MockLogger('test')))
    assert metrics == []
