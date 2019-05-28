VERSION_1_8 = [1, 8, 0]

HARBOR_STATUS_CHECKS = [
    ('harbor.status', None),
    ('harbor.chartmuseum.status', None),
    ('harbor.registry.status', None),
    ('harbor.redis.status', VERSION_1_8),
    ('harbor.jobservice.status', VERSION_1_8),
    ('harbor.registryctl.status', VERSION_1_8),
    ('harbor.portal.status', VERSION_1_8),
    ('harbor.core.status', VERSION_1_8),
    ('harbor.database.status', VERSION_1_8),
]

HARBOR_METRICS = [
    'harbor.projects.count',
    'harbor.disk.free',
    'harbor.disk.total'
]
