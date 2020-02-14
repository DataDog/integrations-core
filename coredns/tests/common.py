CHECK_NAME = 'coredns'
NAMESPACE = 'coredns'

COUNT_METRICS = [
    NAMESPACE + '.request_count',
    NAMESPACE + '.request_type_count',
    NAMESPACE + '.cache_misses_count',
    NAMESPACE + '.cache_hits_count',
    NAMESPACE + '.response_code_count',
    NAMESPACE + '.proxy_request_count',
    NAMESPACE + '.response_size.bytes.count',
    NAMESPACE + '.request_size.bytes.count',
    NAMESPACE + '.proxy_request_duration.seconds.count',
    NAMESPACE + '.request_duration.seconds.count',
    NAMESPACE + '.forward_request_count',
    NAMESPACE + '.forward_request_duration.seconds.count',
    NAMESPACE + '.forward_response_rcode_count',
]

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
    NAMESPACE + '.forward_request_count',
    NAMESPACE + '.forward_request_duration.seconds.sum',
    NAMESPACE + '.forward_request_duration.seconds.count',
    NAMESPACE + '.forward_response_rcode_count',
    NAMESPACE + '.forward_sockets_open',
]
