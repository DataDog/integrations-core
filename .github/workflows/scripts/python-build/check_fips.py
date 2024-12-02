import _hashlib
import hashlib
import ctypes
import sys

if len(sys.argv) != 2:
    print("Usage: python check_fips.py <path_to_openssl_library>")
    sys.exit(1)

openssl = ctypes.CDLL(sys.argv[1])

EVP_default_properties_enable_fips = openssl.EVP_default_properties_enable_fips
EVP_default_properties_enable_fips.argtypes = [ctypes.c_void_p, ctypes.c_int]
EVP_default_properties_enable_fips.restype = ctypes.c_int

# Enable FIPS mode
result = EVP_default_properties_enable_fips(None, 1)
if result != 1:
    raise Exception("Error while try to enable FIPS mode.")


if _hashlib.get_fips_mode():
    print("FIPS mode is enabled.")
else:
    print("FIPS mode is not enabled.")

try:
    md5_hash = hashlib.md5()
    md5_hash.update("Hello, World!".encode('utf-8'))
    hash_result = md5_hash.hexdigest()
    print("MD5 hash of 'Hello, World!':", hash_result)
except _hashlib.UnsupportedDigestmodError:
    print("Success: MD5 is not available in FIPS mode as expected.")
else:
    raise Exception("Error: MD5 hash should not be available in FIPS mode, but it is.")
