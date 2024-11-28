# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
import os
import logging


class FIPSSwitch():

    def enable(self, path_to_embedded: str = None):
        self._set_openssl_env_vars(path_to_embedded)
        # self._enable_openssl_fips(path_to_embedded)
        # self._enable_cryptography_fips(path_to_embedded)

    def disable(self):
        self._clear_openssl_env_vars()
        # self._disable_openssl_fips()

    def _set_openssl_env_vars(self, path_to_embedded: str = None):
        if not (os.getenv("OPENSSL_CONF") and os.getenv("OPENSSL_MODULES")):
            from pathlib import Path

            if path_to_embedded is None:
                import sys

                embedded_dir = "embedded3" if os.name == 'nt' else "embedded"
                path_to_embedded = sys.executable.split("embedded")[0] + embedded_dir
            path_to_embedded = Path(path_to_embedded)
            if not path_to_embedded.exists():
                raise RuntimeError(f'Path "{path_to_embedded}" does not exist')
            # The cryptography package can enter FIPS mode if its internal OpenSSL
            # can access the FIPS module and configuration.
            os.environ["OPENSSL_CONF"] = str(path_to_embedded / "ssl" / "openssl.cnf")
            os.environ["OPENSSL_MODULES"] = str(path_to_embedded / "lib" / "ossl-modules")

    def _clear_openssl_env_vars(self):
        os.environ.pop("OPENSSL_CONF", None)
        os.environ.pop("OPENSSL_MODULES", None)

    def _enable_cryptography_fips(self, path_to_embedded: str = None):
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

    def _enable_openssl_fips(self, path_to_embedded: str = None):
        from cffi import FFI

        ffi = FFI()
        libcrypto = ffi.dlopen("libcrypto-3.dll" if sys.platform == "win32" else "libcrypto.so")
        ffi.cdef(
            """
            int EVP_default_properties_enable_fips(void *ctx, int enable);
        """
        )

        if not libcrypto.EVP_default_properties_enable_fips(ffi.NULL, 1):
            raise RuntimeError("Failed to enable FIPS mode in OpenSSL")
        else:
            logging.info("OpenSSL FIPS mode enabled successfully.")

    def _disable_openssl_fips(self):
        from cffi import FFI

        ffi = FFI()
        libcrypto = ffi.dlopen("libcrypto-3.dll" if sys.platform == "win32" else "libcrypto.so")
        ffi.cdef(
            """
            int EVP_default_properties_enable_fips(void *ctx, int enable);
        """
        )

        if not libcrypto.EVP_default_properties_enable_fips(ffi.NULL, 0):
            raise RuntimeError("Failed to disable FIPS mode in OpenSSL")
        else:
            logging.info("OpenSSL FIPS mode disabled successfully.")

