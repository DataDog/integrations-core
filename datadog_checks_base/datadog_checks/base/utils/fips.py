# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os


def enable_fips(path_to_openssl_conf: str, path_to_openssl_modules: str):
    os.environ["OPENSSL_CONF"] = path_to_openssl_conf
    os.environ["OPENSSL_MODULES"] = path_to_openssl_modules
