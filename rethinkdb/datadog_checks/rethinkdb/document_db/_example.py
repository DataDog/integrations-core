from datadog_checks.rethinkdb.document_db import DocumentQuery, transformers


def make_fake_query():
    # type: () -> list
    # These documents would typically come from calls to a database client library.
    document = {
        'memory': {'total_mb': 1000},
        'disk_used_bytes_mb': 2500,
        'cpus': [{'usage': 50}, {'usage': 10}],
        'threads_per_process': {'server': 12, 'worker': 4},
    }

    # You may construct these tags from data retrieved from the database.
    tags = ['db:main']

    # Return any number of document/tags pairs.
    # Note: yield syntax is supported too, eg `yield (document, tags)`.
    return [(document, tags)]


query = DocumentQuery(
    source=make_fake_query,
    name='system_usage',
    prefix='system',
    metrics=[
        {'type': 'gauge', 'path': 'memory.total_mb'},
        {'type': 'gauge', 'path': 'disk_used_bytes_mb'},
        {'type': 'gauge', 'path': 'cpus', 'name': 'cpus.total', 'transformer': transformers.length},
    ],
    enumerations=[{'path': 'cpus', 'index_tag': 'cpu', 'metrics': [{'type': 'gauge', 'path': 'usage'}]}],
    groups=[{'type': 'gauge', 'path': 'threads_per_process', 'key_tag': 'process'}],
)


assert list(query.run()) == [
    {'type': 'gauge', 'name': 'system.memory.total_mb', 'value': 1000, 'tags': ['db:main']},
    {'type': 'gauge', 'name': 'system.disk_used_bytes_mb', 'value': 2500, 'tags': ['db:main']},
    {'type': 'gauge', 'name': 'system.cpus.total', 'value': 2, 'tags': ['db:main']},
    {'type': 'gauge', 'name': 'system.cpus.usage', 'value': 50, 'tags': ['db:main', 'cpu:0']},
    {'type': 'gauge', 'name': 'system.cpus.usage', 'value': 10, 'tags': ['db:main', 'cpu:1']},
    {'type': 'gauge', 'name': 'system.threads_per_process', 'value': 12, 'tags': ['db:main', 'process:server']},
    {'type': 'gauge', 'name': 'system.threads_per_process', 'value': 4, 'tags': ['db:main', 'process:worker']},
]
