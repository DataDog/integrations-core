# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

if PY2:
    from urllib import quote
else:
    from urllib.parse import quote


def generate_sql_comment(**data):
    '''
    Generate a SQL comment from a dictionary of key-value pairs.
    Returns an empty string if the input dictionary is empty or if all values are empty.
    Example:
    >>> generate_sql_comment(foo='bar', baz='qux')
    "/* baz='qux',foo='bar' */"
    '''
    if not data:
        return ''

    comment = ','.join(
        "{}='{}'".format(quote(key), quote(value)) for key, value in data.items() if value is not None and value != ''
    )

    return '/* {} */'.format(comment)


def add_sql_comment(sql, prepand=True, **data):
    '''
    Prepand or append a SQL comment to a SQL statement from a dictionary of key-value pairs.
    Returns the original SQL statement if the input dictionary is empty or if all values are empty.
    Example:
    >>> add_sql_comment('SELECT * FROM table', foo='bar', baz='qux')
    "/* baz='qux',foo='bar' */ SELECT * FROM table"
    >>> add_sql_comment('SELECT * FROM table', False, foo='bar', baz='qux')
    "SELECT * FROM table /* baz='qux',foo='bar' */"
    '''
    comment = generate_sql_comment(**data)
    if not comment:
        return sql

    sql = sql.strip()
    if not sql:
        return sql

    if prepand:
        sql = f'{comment} {sql}'
    else:
        if sql[-1] == ';':
            sql = '{} {};'.format(sql[:-1], comment)
        else:
            sql = '{} {}'.format(sql, comment)
    return sql
