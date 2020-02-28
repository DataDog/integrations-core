# TLS certificates

TLS certificates were generated using [`trustme-cli`](https://github.com/sethmlarson/trustme-cli):

```bash
trustme-cli --common-name localhost
mv server.key server.pem client.pem rethinkdb/tests/data/tls/
```

To connect to a server configured with these certificates, use:

```python
import os
from rethinkdb import r

ca_certs = os.path.join('rethinkdb', 'tests', 'data', 'tls', 'client.pem')
port = 28016  # TODO: adjust to the server you want to connect to.
conn = r.connect(port=port, ssl={'ca_certs': ca_certs})
```

See also: https://rethinkdb.com/docs/security/#securing-the-driver-port
