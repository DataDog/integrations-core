# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pymongo
from six.moves.urllib.parse import quote_plus, unquote_plus, urlencode, urlunparse


def build_connection_string(hosts, scheme, username=None, password=None, database=None, options=None):
    # type: (list, str, str, str, str, dict) -> str
    """
    Build a server connection string from individual parts. Make sure that parts are properly URL-encoded.

    See https://docs.mongodb.com/manual/reference/connection-string/
    """

    def add_default_port(host):
        # type: (str) -> str
        if ':' not in host:
            return '{}:27017'.format(host)
        return host

    host = ','.join(add_default_port(host) for host in hosts)
    path = '/{}'.format(database) if database else '/'
    if username and password:
        netloc = '{}:{}@{}'.format(quote_plus(username), quote_plus(password), host)
    else:
        netloc = host

    path_params = ""
    query = urlencode(options or {})
    fragment = ""

    return urlunparse([scheme, netloc, path, path_params, query, fragment])


def parse_mongo_uri(server, sanitize_username=False):
    """
    Parses a MongoDB-formatted URI (e.g. mongodb://user:pass@server/db) and returns parsed elements
    and a sanitized URI.
    """
    parsed = pymongo.uri_parser.parse_uri(server)

    username = parsed.get('username')
    password = parsed.get('password')
    db_name = parsed.get('database')
    nodelist = parsed.get('nodelist')
    auth_source = parsed.get('options', {}).get('authsource')

    # Remove password (and optionally username) from sanitized server URI.
    # To ensure that the `replace` works well, we first need to url-decode the raw server string
    # since the password parsed by pymongo is url-decoded
    decoded_server = unquote_plus(server)
    clean_server_name = decoded_server.replace(password, "*" * 5) if password else decoded_server

    if sanitize_username and username:
        username_pattern = u"{}[@:]".format(re.escape(username))
        clean_server_name = re.sub(username_pattern, "", clean_server_name)

    return username, password, db_name, nodelist, clean_server_name, auth_source
