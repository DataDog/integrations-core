import sys


def get_conn_info():
    return {'url': 'http://127.0.0.1:10250'}


def get_tags(entity, high_card):
    return []


kubeutil = type(sys)('kubeutil')
kubeutil.get_connection_info = get_conn_info
sys.modules['kubeutil'] = kubeutil

tagger = type(sys)('tagger')
tagger.get_tags = get_tags
sys.modules['tagger'] = tagger
