import requests
import subprocess

requests.put('http://etcd0:2379/v2/keys/services/redis/01', data={'value': 'redis1:6101'})
requests.put('http://etcd0:2379/v2/keys/services/redis/02', data={'value': 'redis2:6102'})
requests.put('http://etcd0:2379/v2/keys/services/twemproxy/port', data={'value': '6100'})
requests.put('http://etcd0:2379/v2/keys/services/twemproxy/host', data={'value': 'localhost'})

subprocess.check_call(['bash', '/run.sh'])
