import time
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def main():
    with open('/home/run/priv.pem', 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

    serialized_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    now = datetime.now(timezone.utc)
    encoded = jwt.encode(
        {'exp': now + timedelta(hours=1), 'nbf': now, 'aud': 'test', 'name': 'datadog'},
        serialized_private,
        algorithm='RS256',
    )

    with open('/home/jwt/claim', 'wb') as f:
        f.write(encoded)

    while True:
        time.sleep(10)


if __name__ == '__main__':
    main()
