# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

SERVER_METRIC_KEYS = [
    'admin_connections',
    'client_connections',
    'sessions',
    'producers',
    'consumers',
    'topics',
    'queues',
    'durables',
    'pending_messages',
    'pending_message_size',
    'message_memory_pooled',
    'synchronous_storage',
    'asynchronous_storage',
    'inbound_message_rate',
    'inbound_message_rate_size',
    'outbound_message_rate',
    'outbound_message_rate_size',
    'storage_read_rate',
    'storage_read_rate_size',
    'storage_write_rate',
    'storage_write_rate_size',
    'uptime',
]

UNIT_PATTERN = re.compile(r'(?P<value>\d+\.?\d*)\s*(?P<unit>\S+)')

SHOW_METRIC_DATA = {
    'show server': {
        'regex': re.compile(r'^\s*(?P<key>.+?):\s+(?P<value>.+)$'),
        'metric_prefix': 'server',
        'metric_keys': SERVER_METRIC_KEYS,
        'tags': ['version', 'hostname'],
    },
    'show queues': {
        'regex': re.compile(
            r'^\s*[*\s]*(?P<queue_name>\S+)\s+'
            r'(?P<snfgxibct>[-+*]*)\s+'
            r'(?P<pre>\d+\*?)\s+'
            r'(?P<receivers>\d+)\s+'
            r'(?P<pending_messages>\d+)\s+'
            r'(?P<pending_messages_size>\d+\.?\d*\s*\S+)\s+'
            r'(?P<pending_persistent_messages>\d+)\s+'
            r'(?P<pending_persistent_messages_size>\d+\.?\d*\s*\S+)\s*$'
        ),
        'metric_prefix': 'queue',
        'metric_keys': [
            'receivers',
            'pending_messages',
            'pending_messages_size',
            'pending_persistent_messages',
            'pending_persistent_messages_size',
        ],
        'tags': ['queue_name'],
    },
    'show topics': {
        'regex': re.compile(
            r'^\s*[*\s]*(?P<topic_name>\S+)\s+'
            r'(?P<snfgeibctm>[-+*]*)\s+'
            r'(?P<subsciptions>\d+\*?)\s+'
            r'(?P<durable_subscriptions>\d+)\s+'
            r'(?P<pending_messages>\d+)\s+'
            r'(?P<pending_messages_size>\d+\.?\d*\s*\S+)\s+'
            r'(?P<pending_persistent_messages>\d+)\s+'
            r'(?P<pending_persistent_messages_size>\d+\.?\d*\s*\S+)\s*$'
        ),
        'metric_prefix': 'topic',
        'metric_keys': [
            'subsciptions',
            'durable_subscriptions',
            'pending_messages',
            'pending_messages_size',
            'pending_persistent_messages',
            'pending_persistent_messages_size',
        ],
        'tags': ['topic_name'],
    },
    'show stat consumers': {
        'regex': re.compile(
            r'^\s*(?P<user>\S+)\s+'
            r'(?P<conn>\d+)\s+'
            r'(?P<component_type>\S)\s+'
            r'(?P<destination>\S+)\s+'
            r'(?P<total_messages>\d+)\s+'
            r'(?P<total_messages_size>\d+\.?\d*\s*\S+)\s+'
            r'(?P<messages_rate>\d+)\s+'
            r'(?P<messages_rate_size>\d+\.?\d*\s*\S+)\s*$'
        ),
        'metric_prefix': 'consumer',
        'metric_keys': [
            'total_messages',
            'total_messages_size',
            'messages_rate',
            'messages_rate_size',
        ],
        'tags': ['destination', 'user', 'component_type', 'conn', 'destination'],
    },
    'show stat producers': {
        'regex': re.compile(
            r'^\s*(?P<user>\S+)\s+'
            r'(?P<conn>\d+)\s+'
            r'(?P<component_type>\S)\s+'
            r'(?P<destination>\S+)\s+'
            r'(?P<total_messages>\d+)\s+'
            r'(?P<total_messages_size>\d+\.?\d*\s*\S+)\s+'
            r'(?P<messages_rate>\d+)\s+'
            r'(?P<messages_rate_size>\d+\.?\d*\s*\S+)\s*$'
        ),
        'metric_prefix': 'producer',
        'metric_keys': [
            'total_messages',
            'total_messages_size',
            'messages_rate',
            'messages_rate_size',
        ],
        'tags': ['destination', 'user', 'component_type', 'conn', 'destination'],
    },
    'show connections full': {
        'regex': re.compile(
            r'^\s*(?P<client_type>[-#JC])\s+'
            r'(?P<tibco_version>[\w.]+(?:\s+V\d+)?)\s+'
            r'(?P<id>\d+)\s+'
            r'(?P<fsxt>[-A-Za-z]+)\s+'
            r'(?P<s>[+|-])\s+'
            r'(?P<tibco_host>\S+)\s+'
            r'(?P<ip_address>\S+)\s+'
            r'(?P<tibco_port>\d+)\s+'
            r'(?P<user>\S*)\s+'
            r'(?P<client_id>\S*)\s+'
            r'(?P<sessions>\d+)\s+'
            r'(?P<producers>\d+)\s+'
            r'(?P<consumers>\d+)\s+'
            r'(?P<temporary_topics>\d+)\s+'
            r'(?P<temporary_queues>\d+)\s+'
            r'(?P<uncommitted_transactions>\d+)\s+'
            r'(?P<uncommitted_transactions_size>\d+\.?\d*\s*\S*)\s+'
            r'(?P<uptime>\S+)\s*$'
        ),
        'metric_prefix': 'connection',
        'metric_keys': [
            'sessions',
            'producers',
            'consumers',
            'temporary_topics',
            'temporary_queues',
            'uncommitted_transactions',
            'uncommitted_transactions_size',
        ],
        'tags': ['client_type', 'tibco_host', 'ip_address', 'tibco_port', 'user', 'client_id'],
    },
    'show durables': {
        'regex': re.compile(
            r'^\s*(?P<topic_name>\S+)\s+'
            r'(?P<durable>\S+)\s+'
            r'(?P<shared>\S+)\s+'
            r'(?P<user>\S+)\s+'
            r'(?P<pending_messages>\d+)\s+'
            r'(?P<pending_messages_size>\d+\.?\d*\s*\S+)\s*$'
        ),
        'metric_prefix': 'durable',
        'metric_keys': [
            'pending_messages',
            'pending_messages_size',
        ],
        'tags': ['topic_name', 'durable', 'shared', 'user'],
    },
}
