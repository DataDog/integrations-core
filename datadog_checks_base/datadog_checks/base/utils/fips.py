# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os
import sys

LOGGER = logging.getLogger(__file__)


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


def is_enabled():
    enabled = False
    # On Windows, FIPS mode is activated through a registry:
    # https://csrc.nist.gov/CSRC/media/projects/cryptographic-module-validation-program/documents/security-policies/140sp4825.pdf
    # We copy the Agent's implementation for this function:
    # https://github.com/DataDog/datadog-agent/tree/main/pkg/fips
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Lsa\FipsAlgorithmPolicy"
            ) as key:
                fips_registry, _ = winreg.QueryValueEx(key, "Enabled")
                enabled = fips_registry == 1
        except Exception as e:
            LOGGER.debug(
                "Windows error encountered when fetching FipsAlgorithmPolicy registry key,\
                    assuming FIPS mode is disabled: %s",
                e,
            )
    else:
        enabled = os.environ.get("GOFIPS", "0") == "1"
    return enabled


def _get_embedded_path():
    import sys
    from pathlib import Path

    embedded_dir = "embedded3" if os.name == 'nt' else "embedded"
    return Path(sys.executable.split("embedded")[0] + embedded_dir)
