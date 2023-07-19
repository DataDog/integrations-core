{license_header}

{documentation}

def shared_new_gc_metrics(field, value):
    return False


def instance_collect_default_jvm_metrics(field, value):
    return True


def instance_empty_default_hostname(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_rmi_client_timeout(field, value):
    return 15000


def instance_rmi_connection_timeout(field, value):
    return 20000


def instance_rmi_registry_ssl(field, value):
    return False
