CHECK_NAME = 'coredns'
NAMESPACE = 'coredns'

METRICS = [
    NAMESPACE + '.request_count',
    NAMESPACE + '.cache_size.count',
    NAMESPACE + '.request_type_count',
    NAMESPACE + '.cache_misses_count',
    NAMESPACE + '.response_code_count',
    NAMESPACE + '.proxy_request_count',
    NAMESPACE + '.response_size.bytes.sum',
    NAMESPACE + '.response_size.bytes.count',
    NAMESPACE + '.request_size.bytes.sum',
    NAMESPACE + '.request_size.bytes.count',
    NAMESPACE + '.proxy_request_duration.seconds.sum',
    NAMESPACE + '.proxy_request_duration.seconds.count',
    NAMESPACE + '.request_duration.seconds.sum',
    NAMESPACE + '.request_duration.seconds.count',
]
