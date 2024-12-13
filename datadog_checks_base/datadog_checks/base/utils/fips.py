# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import sys
import logging


def enable_fips(path_to_openssl_conf: str, path_to_openssl_modules: str):
    os.environ["OPENSSL_CONF"] = path_to_openssl_conf
    os.environ["OPENSSL_MODULES"] = path_to_openssl_modules


def _enable_openssl_fips():
    from cffi import FFI

    ffi = FFI()
    libcrypto = ffi.dlopen("libcrypto-3.dll" if sys.platform == "win32" else "libcrypto.so")
    ffi.cdef( """
        int EVP_default_properties_enable_fips(void *ctx, int enable);
    """
    )

    if not libcrypto.EVP_default_properties_enable_fips(ffi.NULL, 1):
        raise RuntimeError("Failed to enable FIPS mode in OpenSSL")
    else:
        logging.info("OpenSSL FIPS mode enabled successfully.")


def _enable_cryptography_fips():
    from cryptography.exceptions import InternalError
    from cryptography.hazmat.backends import default_backend

    cryptography_backend = default_backend()
    try:
        cryptography_backend._enable_fips()
        pass
    except InternalError as e:
        logging.error("FIPS mode could not be enabled.")
        raise e
    if not cryptography_backend._fips_enabled:
        logging.error("FIPS mode was not enabled successfully.")
        raise RuntimeError("FIPS is not enabled.")
