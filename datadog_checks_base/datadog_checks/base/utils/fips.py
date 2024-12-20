# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os


def enable_fips(path_to_openssl_conf=None, path_to_openssl_modules=None):
    path_to_embedded = None
    if os.getenv("OPENSSL_CONF") is None:
        if path_to_openssl_conf is None:
            path_to_embedded = _get_embedded_path() if path_to_embedded is None else path_to_embedded
            path_to_openssl_conf = path_to_embedded / "ssl" / "openssl.cnf"
            if not path_to_openssl_conf.exists():
                raise RuntimeError(f'The configuration file "{path_to_openssl_conf}" does not exist')
        os.environ["OPENSSL_CONF"] = str(path_to_openssl_conf)

    if os.getenv("OPENSSL_MODULES") is None:
        if path_to_openssl_modules is None:
            path_to_embedded = _get_embedded_path() if path_to_embedded is None else path_to_embedded
            path_to_openssl_modules = path_to_embedded / "lib" / "ossl-modules"
            if not path_to_openssl_conf.exists():
                raise RuntimeError(f'The directory "{path_to_openssl_modules}" does not exist')
        os.environ["OPENSSL_MODULES"] = str(path_to_openssl_modules)


def _get_embedded_path():
    import sys
    from pathlib import Path

    embedded_dir = "embedded3" if os.name == 'nt' else "embedded"
    return Path(sys.executable.split("embedded")[0] + embedded_dir)
