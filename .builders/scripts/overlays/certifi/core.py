"""
certifi.py
~~~~~~~~~~

Datadog Agent build of certifi: returns the location or contents of the Agent's
embedded CA bundle instead of a bundle shipped in this package, so every library
that asks certifi for CAs trusts the same list as the Agent's OpenSSL.
"""

import os
import sys


def where() -> str:
    # The embedded OpenSSL's default CA file: `embedded/ssl/cert.pem` on Linux and
    # macOS, `embedded3\ssl\cert.pem` on Windows. The Agent sets the Python home to
    # that `embedded` directory, so it is `sys.prefix` both in-process and in
    # `embedded/bin/python3`.
    return os.path.join(sys.prefix, "ssl", "cert.pem")


def contents() -> str:
    # The Agent's bundle comes from curl.se and has UTF-8 in its comments, unlike
    # certifi's own ASCII-only file.
    with open(where(), encoding="utf-8") as f:
        return f.read()
