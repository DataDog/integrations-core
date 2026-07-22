{license_header}

{documentation}


def shared_new_gc_metrics():
    return False


def instance_collect_default_jvm_metrics():
    return True


def instance_empty_default_hostname():
    return False


def instance_min_collection_interval():
    return 15


def instance_rmi_client_timeout():
    return 15000


def instance_rmi_connection_timeout():
    return 20000


def instance_rmi_registry_ssl():
    return False
