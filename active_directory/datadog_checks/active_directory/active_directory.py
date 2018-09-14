# (C) Datadog, Inc. 2013-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# datadog
from datadog_checks.checks.win import PDHBaseCheck

DEFAULT_COUNTERS = [
    # counterset, instance of counter, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor active directory:
    # https://technet.microsoft.com/en-us/library/cc961942.aspx
    ["NTDS", None, "DRA Inbound Bytes Compressed (Between Sites, After Compression)/sec",   "active_directory.dra.inbound.bytes.after_compression",  "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Bytes Compressed (Between Sites, Before Compression)/sec",  "active_directory.dra.inbound.bytes.before_compression", "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Bytes Not Compressed (Within Site)/sec",                    "active_directory.dra.inbound.bytes.not_compressed",     "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Bytes Total/sec",                                           "active_directory.dra.inbound.bytes.total",              "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Full Sync Objects Remaining",                               "active_directory.dra.inbound.objects.remaining",        "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Objects/sec",                                               "active_directory.dra.inbound.objects.persec",           "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Objects Applied/sec",                                       "active_directory.dra.inbound.objects.applied_persec",   "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Objects Filtered/sec",                                      "active_directory.dra.inbound.objects.filtered_persec",  "gauge"],  # noqa: E501

    ["NTDS", None, "DRA Inbound Object Updates Remaining in Packet",                        "active_directory.dra.inbound.objects.remaining_in_packet", "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Properties Applied/sec",                                    "active_directory.dra.inbound.properties.applied_persec", "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Properties Filtered/sec",                                   "active_directory.dra.inbound.properties.filtered_persec", "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Properties Total/sec",                                      "active_directory.dra.inbound.properties.total_persec",  "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Values (DNs only)/sec",                                     "active_directory.dra.inbound.values.dns_persec",        "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Inbound Values Total/sec",                                          "active_directory.dra.inbound.values.total_persec",        "gauge"],  # noqa: E501

    ["NTDS", None, "DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec",   "active_directory.dra.outbound.bytes.after_compression",  "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Outbound Bytes Compressed (Between Sites, Before Compression)/sec",  "active_directory.dra.outbound.bytes.before_compression", "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Outbound Bytes Not Compressed (Within Site)/sec",                    "active_directory.dra.outbound.bytes.not_compressed",     "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Outbound Bytes Total/sec",                                           "active_directory.dra.outbound.bytes.total",              "gauge"],  # noqa: E501

    ["NTDS", None, "DRA Outbound Objects Filtered/sec",                                      "active_directory.dra.outbound.objects.filtered_persec",  "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Outbound Objects/sec",                                               "active_directory.dra.outbound.objects.persec",           "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Outbound Properties/sec",                                            "active_directory.dra.outbound.properties.persec",           "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Outbound Values (DNs only)/sec",                                     "active_directory.dra.outbound.values.dns_persec",        "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Outbound Values Total/sec",                                          "active_directory.dra.outbound.values.total_persec",        "gauge"],  # noqa: E501

    # ["NTDS", None, "DRA Remaining Replication Updates",                                    "active_directory.dra.replication.remaining_updates",        "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Pending Replication Synchronizations",                               "active_directory.dra.replication.pending_synchronizations", "gauge"],  # noqa: E501
    ["NTDS", None, "DRA Sync Requests Made",                                                 "active_directory.dra.sync_requests_made",                   "gauge"],  # noqa: E501

    # ["NTDS", None, "DS Security Descriptor Suboperations/sec",                             "active_directory.ds.security_descriptor.subops_persec",      "gauge"],  # noqa: E501
    # ["NTDS", None, "DS Security Descriptor Propagation Events",                            "active_directory.ds.security_descriptor.propagation_events", "gauge"],  # noqa: E501
    ["NTDS", None, "DS Threads in Use",                                                      "active_directory.ds.threads_in_use",                         "gauge"],  # noqa: E501

    ["NTDS", None, "LDAP Client Sessions",                                                   "active_directory.ldap.client_sessions",                      "gauge"],  # noqa: E501
    ["NTDS", None, "LDAP Bind Time",                                                         "active_directory.ldap.bind_time",                            "gauge"],  # noqa: E501
    ["NTDS", None, "LDAP Successful Binds/sec",                                              "active_directory.ldap.successful_binds_persec",              "gauge"],  # noqa: E501
    ["NTDS", None, "LDAP Searches/sec",                                                      "active_directory.ldap.searches_persec",                      "gauge"],  # noqa: E501

    # ["NTDS", None, "Kerberos Authentications/sec",                                         "active_directory.kerberos.auths_persec",                     "gauge"],  # noqa: E501
    # ["NTDS", None, "NTLM Authentications/sec",                                             "active_directory.ntlm.auths_persec",                         "gauge"],  # noqa: E501
]


class ActiveDirectoryCheck(PDHBaseCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        PDHBaseCheck.__init__(self, name, init_config, agentConfig, instances=instances, counter_list=DEFAULT_COUNTERS)
