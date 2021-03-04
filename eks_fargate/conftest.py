import sys


def get_conn_info():
    return {'url': 'http://127.0.0.1:10255'}


kubeutil = type(sys)('kubeutil')
kubeutil.get_connection_info = get_conn_info
sys.modules['kubeutil'] = kubeutil
