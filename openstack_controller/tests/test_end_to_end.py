# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# flake8: noqa
import copy
import mock
from datadog_checks.openstack_controller import OpenStackControllerCheck

PROJECTS = {u'projects': [{u'is_domain': False, u'description': u'Bootstrap project for initializing the cloud.',
                           u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************3fb11'},
                           u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                           u'id': u'***************************3fb11', u'name': u'admin'},
                          {u'is_domain': False, u'description': u'test project',
                           u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************73dbe'},
                           u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                           u'id': u'***************************73dbe', u'name': u'testProj1'},
                          {u'is_domain': False, u'description': u'test project',
                           u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************147d1'},
                           u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                           u'id': u'***************************147d1', u'name': u'12345'},
                          {u'is_domain': False, u'description': u'Keystone Identity Service',
                           u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************4bfc1'},
                           u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                           u'id': u'***************************4bfc1', u'name': u'service'},
                          {u'is_domain': False, u'description': u'',
                           u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************44736'},
                           u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                           u'id': u'***************************44736', u'name': u'abcde'},
                          {u'is_domain': False, u'description': u'test project',
                           u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************d91a1'},
                           u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                           u'id': u'***************************d91a1', u'name': u'testProj2'}],
            u'links': {u'self': u'http://10.0.2.15:5000/v3/projects', u'next': None, u'previous': None}}


def make_request_responses(url, header, params=None, timeout=None):
    if url == "http://10.0.2.15:5000/v3/projects":
        return PROJECTS
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/limits":
        if params.get("tenant_id") == u'***************************d91a1':
            return {u'limits': {u'rate': [],
                                u'absolute': {u'maxServerMeta': 128, u'maxTotalInstances': 20, u'maxPersonality': 5,
                                              u'totalServerGroupsUsed': 0, u'maxImageMeta': 128,
                                              u'maxPersonalitySize': 10240, u'maxTotalRAMSize': 51200,
                                              u'maxServerGroups': 10, u'maxSecurityGroupRules': 20,
                                              u'maxTotalKeypairs': 100, u'totalCoresUsed': 0, u'totalRAMUsed': 0,
                                              u'maxSecurityGroups': 10, u'totalFloatingIpsUsed': 0,
                                              u'totalInstancesUsed': 0, u'maxServerGroupMembers': 10,
                                              u'maxTotalFloatingIps': 10, u'totalSecurityGroupsUsed': 0,
                                              u'maxTotalCores': 40}}}
        elif params.get("tenant_id") == u'***************************4bfc1':
            return {u'limits': {u'rate': [],
                                u'absolute': {u'maxServerMeta': 128, u'maxTotalInstances': 10, u'maxPersonality': 5,
                                              u'totalServerGroupsUsed': 0, u'maxImageMeta': 128,
                                              u'maxPersonalitySize': 10240, u'maxTotalRAMSize': 51200,
                                              u'maxServerGroups': 10, u'maxSecurityGroupRules': 20,
                                              u'maxTotalKeypairs': 100, u'totalCoresUsed': 0, u'totalRAMUsed': 0,
                                              u'maxSecurityGroups': 10, u'totalFloatingIpsUsed': 0,
                                              u'totalInstancesUsed': 0, u'maxServerGroupMembers': 10,
                                              u'maxTotalFloatingIps': 10, u'totalSecurityGroupsUsed': 0,
                                              u'maxTotalCores': 20}}}
        elif params.get("tenant_id") == u'***************************73dbe':
            return {u'limits': {u'rate': [],
                                u'absolute': {u'maxServerMeta': 128, u'maxTotalInstances': 20, u'maxPersonality': 5,
                                              u'totalServerGroupsUsed': 0, u'maxImageMeta': 128,
                                              u'maxPersonalitySize': 10240, u'maxTotalRAMSize': 51200,
                                              u'maxServerGroups': 10, u'maxSecurityGroupRules': 20,
                                              u'maxTotalKeypairs': 100, u'totalCoresUsed': 2, u'totalRAMUsed': 1024,
                                              u'maxSecurityGroups': 10, u'totalFloatingIpsUsed': 0,
                                              u'totalInstancesUsed': 1, u'maxServerGroupMembers': 10,
                                              u'maxTotalFloatingIps': 10, u'totalSecurityGroupsUsed': 1,
                                              u'maxTotalCores': 40}}}
        elif params.get("tenant_id") == u'***************************3fb11':
            return {u'limits': {u'rate': [],
                                u'absolute': {u'maxServerMeta': 128, u'maxTotalInstances': 20, u'maxPersonality': 10,
                                              u'totalServerGroupsUsed': 0, u'maxImageMeta': 128,
                                              u'maxPersonalitySize': 10240, u'maxTotalRAMSize': 51200,
                                              u'maxServerGroups': 10, u'maxSecurityGroupRules': 20,
                                              u'maxTotalKeypairs': 100, u'totalCoresUsed': 34, u'totalRAMUsed': 17408,
                                              u'maxSecurityGroups': 10, u'totalFloatingIpsUsed': 0,
                                              u'totalInstancesUsed': 17, u'maxServerGroupMembers': 10,
                                              u'maxTotalFloatingIps': 10, u'totalSecurityGroupsUsed': 1,
                                              u'maxTotalCores': 40}}}
        elif params.get("tenant_id") == u'***************************44736':
            return {u'limits': {u'rate': [],
                                u'absolute': {u'maxServerMeta': 128, u'maxTotalInstances': 20, u'maxPersonality': 5,
                                              u'totalServerGroupsUsed': 0, u'maxImageMeta': 128,
                                              u'maxPersonalitySize': 10240, u'maxTotalRAMSize': 51200,
                                              u'maxServerGroups': 10, u'maxSecurityGroupRules': 20,
                                              u'maxTotalKeypairs': 100, u'totalCoresUsed': 0, u'totalRAMUsed': 0,
                                              u'maxSecurityGroups': 10, u'totalFloatingIpsUsed': 0,
                                              u'totalInstancesUsed': 0, u'maxServerGroupMembers': 10,
                                              u'maxTotalFloatingIps': 10, u'totalSecurityGroupsUsed': 0,
                                              u'maxTotalCores': 40}}}
        elif params.get("tenant_id") == u'***************************147d1':
            return {u'limits': {u'rate': [],
                                u'absolute': {u'maxServerMeta': 128, u'maxTotalInstances': 20, u'maxPersonality': 5,
                                              u'totalServerGroupsUsed': 0, u'maxImageMeta': 128,
                                              u'maxPersonalitySize': 10240, u'maxTotalRAMSize': 51200,
                                              u'maxServerGroups': 10, u'maxSecurityGroupRules': 20,
                                              u'maxTotalKeypairs': 100, u'totalCoresUsed': 0, u'totalRAMUsed': 0,
                                              u'maxSecurityGroups': 10, u'totalFloatingIpsUsed': 0,
                                              u'totalInstancesUsed': 0, u'maxServerGroupMembers': 10,
                                              u'maxTotalFloatingIps': 10, u'totalSecurityGroupsUsed': 0,
                                              u'maxTotalCores': 40}}}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/os-hypervisors/detail":
        return {u'hypervisors': [
            {u'status': u'enabled', u'service': {u'host': u'compute1', u'disabled_reason': None, u'id': 2},
             u'vcpus_used': 4, u'hypervisor_type': u'QEMU', u'id': 1, u'local_gb_used': 22, u'state': u'up',
             u'hypervisor_hostname': u'compute1.openstack.local', u'host_ip': u'172.29.236.102', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 3886, u'running_vms': 2, u'free_disk_gb': 26,
             u'hypervisor_version': 2005000, u'disk_available_least': 14, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 4096},
            {u'status': u'enabled', u'service': {u'host': u'compute2', u'disabled_reason': None, u'id': 3},
             u'vcpus_used': 6, u'hypervisor_type': u'QEMU', u'id': 2, u'local_gb_used': 32, u'state': u'up',
             u'hypervisor_hostname': u'compute2.openstack.local', u'host_ip': u'172.29.236.103', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 2862, u'running_vms': 3, u'free_disk_gb': 16,
             u'hypervisor_version': 2005000, u'disk_available_least': -2, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 5120},
            {u'status': u'enabled', u'service': {u'host': u'compute3', u'disabled_reason': None, u'id': 8},
             u'vcpus_used': 0, u'hypervisor_type': u'QEMU', u'id': 8, u'local_gb_used': 2, u'state': u'up',
             u'hypervisor_hostname': u'compute3.openstack.local', u'host_ip': u'172.29.236.103', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 5934, u'running_vms': 0, u'free_disk_gb': 46,
             u'hypervisor_version': 2005000, u'disk_available_least': 38, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "ssbd", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 2048},
            {u'status': u'enabled', u'service': {u'host': u'compute4', u'disabled_reason': None, u'id': 9},
             u'vcpus_used': 6, u'hypervisor_type': u'QEMU', u'id': 9, u'local_gb_used': 32, u'state': u'up',
             u'hypervisor_hostname': u'compute4.openstack.local', u'host_ip': u'172.29.236.116', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 2862, u'running_vms': 3, u'free_disk_gb': 16,
             u'hypervisor_version': 2005000, u'disk_available_least': 2, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "ssbd", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 5120},
            {u'status': u'enabled', u'service': {u'host': u'compute5', u'disabled_reason': None, u'id': 10},
             u'vcpus_used': 4, u'hypervisor_type': u'QEMU', u'id': 10, u'local_gb_used': 22, u'state': u'up',
             u'hypervisor_hostname': u'compute5.openstack.local', u'host_ip': u'172.29.236.117', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 3886, u'running_vms': 2, u'free_disk_gb': 26,
             u'hypervisor_version': 2005000, u'disk_available_least': 14, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "ssbd", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 4096},
            {u'status': u'enabled', u'service': {u'host': u'compute6', u'disabled_reason': None, u'id': 11},
             u'vcpus_used': 0, u'hypervisor_type': u'QEMU', u'id': 11, u'local_gb_used': 2, u'state': u'up',
             u'hypervisor_hostname': u'compute6.openstack.local', u'host_ip': u'172.29.236.118', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 5934, u'running_vms': 0, u'free_disk_gb': 46,
             u'hypervisor_version': 2005000, u'disk_available_least': 37, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 2048},
            {u'status': u'enabled', u'service': {u'host': u'compute7', u'disabled_reason': None, u'id': 12},
             u'vcpus_used': 6, u'hypervisor_type': u'QEMU', u'id': 12, u'local_gb_used': 32, u'state': u'up',
             u'hypervisor_hostname': u'compute7.openstack.local', u'host_ip': u'172.29.236.119', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 2862, u'running_vms': 3, u'free_disk_gb': 16,
             u'hypervisor_version': 2005000, u'disk_available_least': 3, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "ssbd", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 5120},
            {u'status': u'enabled', u'service': {u'host': u'compute8', u'disabled_reason': None, u'id': 13},
             u'vcpus_used': 4, u'hypervisor_type': u'QEMU', u'id': 13, u'local_gb_used': 22, u'state': u'up',
             u'hypervisor_hostname': u'compute8.openstack.local', u'host_ip': u'172.29.236.120', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 3886, u'running_vms': 2, u'free_disk_gb': 26,
             u'hypervisor_version': 2005000, u'disk_available_least': 13, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "ssbd", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 4096},
            {u'status': u'enabled', u'service': {u'host': u'compute9', u'disabled_reason': None, u'id': 14},
             u'vcpus_used': 0, u'hypervisor_type': u'QEMU', u'id': 14, u'local_gb_used': 2, u'state': u'up',
             u'hypervisor_hostname': u'compute9.openstack.local', u'host_ip': u'172.29.236.121', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 5934, u'running_vms': 0, u'free_disk_gb': 46,
             u'hypervisor_version': 2005000, u'disk_available_least': 3, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "ssbd", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 2048},
            {u'status': u'enabled', u'service': {u'host': u'compute10', u'disabled_reason': None, u'id': 15},
             u'vcpus_used': 6, u'hypervisor_type': u'QEMU', u'id': 15, u'local_gb_used': 32, u'state': u'up',
             u'hypervisor_hostname': u'compute10.openstack.local', u'host_ip': u'172.29.236.122', u'memory_mb': 7982,
             u'current_workload': 0, u'vcpus': 8, u'free_ram_mb': 2862, u'running_vms': 3, u'free_disk_gb': 16,
             u'hypervisor_version': 2005000, u'disk_available_least': 3, u'local_gb': 48,
             u'cpu_info': u'{"vendor": "Intel", "model": "Haswell-noTSX-IBRS", "arch": "x86_64", "features": ["pge", "avx", "clflush", "sep", "syscall", "vme", "invpcid", "tsc", "fsgsbase", "xsave", "spec-ctrl", "vmx", "erms", "cmov", "smep", "ssse3", "pat", "lm", "msr", "nx", "fxsr", "sse4.1", "pae", "sse4.2", "pclmuldq", "ssbd", "fma", "tsc-deadline", "mmx", "osxsave", "cx8", "mce", "de", "rdtscp", "ht", "pse", "lahf_lm", "abm", "popcnt", "mca", "pdpe1gb", "apic", "sse", "f16c", "pni", "aes", "avx2", "sse2", "ss", "hypervisor", "bmi1", "bmi2", "pcid", "fpu", "cx16", "pse36", "mtrr", "movbe", "rdrand", "x2apic"], "topology": {"cores": 8, "cells": 1, "threads": 1, "sockets": 1}}',
             u'memory_mb_used': 5120}]}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/os-aggregates":
        return {u'aggregates': [{u'name': u'test-aggregate', u'availability_zone': u'nova', u'deleted': False,
                                 u'created_at': u'2018-10-05T00:37:02.000000', u'updated_at': None,
                                 u'hosts': [u'compute1'], u'deleted_at': None, u'id': 1,
                                 u'metadata': {u'availability_zone': u'nova'}}]}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/detail":
        return {u'servers': [{u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
            {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:fa:af:ec', u'version': 4, u'addr': u'10.0.0.29',
             u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                             u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/57030997-f1b5-4f79-9429-8cb285318633',
                                                             u'rel': u'self'}, {
                                                             u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/57030997-f1b5-4f79-9429-8cb285318633',
                                                             u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000049',
                              u'OS-SRV-USG:launched_at': u'2018-09-06T17:58:33.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'57030997-f1b5-4f79-9429-8cb285318633',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-09-06T17:58:33Z',
                              u'hostId': u'1aad0cf1b6b677fd293b8d6a445ed37186ad540250ab3d93b309859b',
                              u'OS-EXT-SRV-ATTR:host': u'compute4', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute4.openstack.local',
                              u'name': u'blacklistServer', u'created': u'2018-09-06T17:57:38Z',
                              u'tenant_id': u'***************************73dbe',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:fd:72:ff', u'version': 4,
                                  u'addr': u'10.0.0.27', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7324440d-915b-4e12-8b85-ec8c9a524d6c',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/7324440d-915b-4e12-8b85-ec8c9a524d6c',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000048',
                              u'OS-SRV-USG:launched_at': u'2018-09-06T17:54:56.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'7324440d-915b-4e12-8b85-ec8c9a524d6c',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-10-30T14:28:14Z',
                              u'hostId': u'c457d054e8e619fe3bb0ff756ef7d7ff1adf84031379a91291984a32',
                              u'OS-EXT-SRV-ATTR:host': u'compute7', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute7.openstack.local',
                              u'name': u'blacklist', u'created': u'2018-09-06T17:54:32Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:0c:17:0e', u'version': 4,
                                  u'addr': u'10.0.0.26', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/836f724f-0028-4dc0-b9bd-e0843d767ca2',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/836f724f-0028-4dc0-b9bd-e0843d767ca2',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000044',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:31:10.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'836f724f-0028-4dc0-b9bd-e0843d767ca2',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-10-30T14:28:51Z',
                              u'hostId': u'c457d054e8e619fe3bb0ff756ef7d7ff1adf84031379a91291984a32',
                              u'OS-EXT-SRV-ATTR:host': u'compute7', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute7.openstack.local',
                              u'name': u'finalDestination-8', u'created': u'2018-08-28T21:30:09Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:ca:63:58', u'version': 4,
                                  u'addr': u'10.0.0.11', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/1cc21586-8d43-40ea-bdc9-6f54a79957b4',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/1cc21586-8d43-40ea-bdc9-6f54a79957b4',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000043',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:31:07.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'1cc21586-8d43-40ea-bdc9-6f54a79957b4',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-28T21:31:07Z',
                              u'hostId': u'976f9000397fa853e174f15a55078a8297712a9c5005d2f6009af0ec',
                              u'OS-EXT-SRV-ATTR:host': u'compute8', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute8.openstack.local',
                              u'name': u'finalDestination-7', u'created': u'2018-08-28T21:30:09Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:fd:a9:fc', u'version': 4,
                                  u'addr': u'10.0.0.16', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/acb4197c-f54e-488e-a40a-1b7f59cc9117',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/acb4197c-f54e-488e-a40a-1b7f59cc9117',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000042',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:31:07.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'acb4197c-f54e-488e-a40a-1b7f59cc9117',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-28T21:31:07Z',
                              u'hostId': u'935f7d4e027a256785942c3e8173b02efc5a8a4531ede52d7871adb9',
                              u'OS-EXT-SRV-ATTR:host': u'compute10', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute10.openstack.local',
                              u'name': u'finalDestination-6', u'created': u'2018-08-28T21:30:09Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:18:51:79', u'version': 4,
                                  u'addr': u'10.0.0.21', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/5357e70e-f12c-4bb7-85a2-b40d642a7e92',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/5357e70e-f12c-4bb7-85a2-b40d642a7e92',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000041',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:31:02.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'5357e70e-f12c-4bb7-85a2-b40d642a7e92',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-28T21:31:02Z',
                              u'hostId': u'666fc5e7cbf246b9ea99396e890265fb556e8bc527308f93d76d10a3',
                              u'OS-EXT-SRV-ATTR:host': u'compute5', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute5.openstack.local',
                              u'name': u'finalDestination-5', u'created': u'2018-08-28T21:30:08Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:90:46:f2', u'version': 4,
                                  u'addr': u'10.0.0.22', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7e622c28-4b12-4a58-8ac2-4a2e854f84eb',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/7e622c28-4b12-4a58-8ac2-4a2e854f84eb',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000040',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:31:28.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-10-30T14:28:52Z',
                              u'hostId': u'c457d054e8e619fe3bb0ff756ef7d7ff1adf84031379a91291984a32',
                              u'OS-EXT-SRV-ATTR:host': u'compute7', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute7.openstack.local',
                              u'name': u'finalDestination-4', u'created': u'2018-08-28T21:30:08Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:ff:4e:d6', u'version': 4, u'addr': u'10.0.0.3',
                                  u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                  u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/52561f29-e479-43d7-85de-944d29ef178d',
                                                                                  u'rel': u'self'}, {
                                                                                  u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/52561f29-e479-43d7-85de-944d29ef178d',
                                                                                  u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000003e',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:31:06.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'52561f29-e479-43d7-85de-944d29ef178d',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-28T21:31:06Z',
                              u'hostId': u'976f9000397fa853e174f15a55078a8297712a9c5005d2f6009af0ec',
                              u'OS-EXT-SRV-ATTR:host': u'compute8', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute8.openstack.local',
                              u'name': u'finalDestination-2', u'created': u'2018-08-28T21:30:08Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:ea:21:2e', u'version': 4,
                                  u'addr': u'10.0.0.13', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/4d7cb923-788f-4b61-9061-abfc576ecc1a',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/4d7cb923-788f-4b61-9061-abfc576ecc1a',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000003d',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:30:45.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'4d7cb923-788f-4b61-9061-abfc576ecc1a',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-30T18:02:12Z',
                              u'hostId': u'935f7d4e027a256785942c3e8173b02efc5a8a4531ede52d7871adb9',
                              u'OS-EXT-SRV-ATTR:host': u'compute10', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute10.openstack.local',
                              u'name': u'finalDestination-1', u'created': u'2018-08-28T21:30:08Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:94:44:4f', u'version': 4,
                                  u'addr': u'10.0.0.15', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/ff2f581c-5d03-4a27-a0ba-f102603fe38f',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/ff2f581c-5d03-4a27-a0ba-f102603fe38f',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000003c',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:28:20.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'ff2f581c-5d03-4a27-a0ba-f102603fe38f',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-28T21:28:20Z',
                              u'hostId': u'2e0f037ec53ab532b4d57191af2382d562a863f17ce66592c9bd7fa4',
                              u'OS-EXT-SRV-ATTR:host': u'compute4', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute4.openstack.local',
                              u'name': u'server_take_zero-2', u'created': u'2018-08-28T21:27:55Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:bb:13:9c', u'version': 4,
                                  u'addr': u'10.0.0.10', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7eaa751c-1e37-4963-a836-0a28bc283a9a',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/7eaa751c-1e37-4963-a836-0a28bc283a9a',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000003b',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:28:44.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'7eaa751c-1e37-4963-a836-0a28bc283a9a',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-28T21:28:45Z',
                              u'hostId': u'2e0f037ec53ab532b4d57191af2382d562a863f17ce66592c9bd7fa4',
                              u'OS-EXT-SRV-ATTR:host': u'compute4', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute4.openstack.local',
                              u'name': u'server_take_zero-1', u'created': u'2018-08-28T21:27:55Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:9f:25:1a', u'version': 4,
                                  u'addr': u'10.0.0.23', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/4ceb4c69-a332-4b9d-907b-e99635aae644',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/4ceb4c69-a332-4b9d-907b-e99635aae644',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000003a',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:24:22.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'4ceb4c69-a332-4b9d-907b-e99635aae644',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-28T21:24:22Z',
                              u'hostId': u'666fc5e7cbf246b9ea99396e890265fb556e8bc527308f93d76d10a3',
                              u'OS-EXT-SRV-ATTR:host': u'compute5', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute5.openstack.local',
                              u'name': u'moarserver-13', u'created': u'2018-08-28T21:23:08Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:f3:33:58', u'version': 4,
                                  u'addr': u'10.0.0.14', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/30888944-fb39-4590-9073-ef977ac1f039',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/30888944-fb39-4590-9073-ef977ac1f039',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000002d',
                              u'OS-SRV-USG:launched_at': u'2018-08-28T21:04:22.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'30888944-fb39-4590-9073-ef977ac1f039',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-30T17:58:51Z',
                              u'hostId': u'935f7d4e027a256785942c3e8173b02efc5a8a4531ede52d7871adb9',
                              u'OS-EXT-SRV-ATTR:host': u'compute10', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute10.openstack.local',
                              u'name': u'anotherServer', u'created': u'2018-08-28T21:03:57Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:f7:c5:e6', u'version': 4,
                                  u'addr': u'10.0.0.12', u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                                         u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/b3c8eee3-7e22-4a7c-9745-759073673cbe',
                                                                                                         u'rel': u'self'},
                                                                                                     {
                                                                                                         u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/b3c8eee3-7e22-4a7c-9745-759073673cbe',
                                                                                                         u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000025',
                              u'OS-SRV-USG:launched_at': u'2018-08-20T15:23:32.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'b3c8eee3-7e22-4a7c-9745-759073673cbe',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-10-30T14:28:29Z',
                              u'hostId': u'4f626f6cfa8254516f9878d09dfd657cea28d7260eaa23dd65f5f138',
                              u'OS-EXT-SRV-ATTR:host': u'compute2', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute2.openstack.local',
                              u'name': u'jnrgjoner', u'created': u'2018-08-20T15:23:05Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:34:5e:38', u'version': 4, u'addr': u'10.0.0.5',
                                  u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                  u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/412c79b2-25f2-44d6-8e3b-be4baee11a7f',
                                                                                  u'rel': u'self'}, {
                                                                                  u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/412c79b2-25f2-44d6-8e3b-be4baee11a7f',
                                                                                  u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000024',
                              u'OS-SRV-USG:launched_at': u'2018-08-16T22:46:46.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'412c79b2-25f2-44d6-8e3b-be4baee11a7f',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-31T17:32:20Z',
                              u'hostId': u'4f626f6cfa8254516f9878d09dfd657cea28d7260eaa23dd65f5f138',
                              u'OS-EXT-SRV-ATTR:host': u'compute2', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute2.openstack.local',
                              u'name': u'ReadyServerOne', u'created': u'2018-08-16T22:46:24Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:25:1a:f2', u'version': 4, u'addr': u'10.0.0.7',
                                  u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                  u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/1b7a987f-c4fb-4b6b-aad9-3b461df2019d',
                                                                                  u'rel': u'self'}, {
                                                                                  u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/1b7a987f-c4fb-4b6b-aad9-3b461df2019d',
                                                                                  u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000023',
                              u'OS-SRV-USG:launched_at': u'2018-08-16T22:40:32.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-10-30T14:28:58Z',
                              u'hostId': u'4f626f6cfa8254516f9878d09dfd657cea28d7260eaa23dd65f5f138',
                              u'OS-EXT-SRV-ATTR:host': u'compute2', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute2.openstack.local',
                              u'name': u'HoneyIShrunkTheServer', u'created': u'2018-08-16T22:40:09Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:b1:9c:61', u'version': 4, u'addr': u'10.0.0.9',
                                  u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                  u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/2e1ce152-b19d-4c4a-9cc7-0d150fa97a18',
                                                                                  u'rel': u'self'}, {
                                                                                  u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/2e1ce152-b19d-4c4a-9cc7-0d150fa97a18',
                                                                                  u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000001c',
                              u'OS-SRV-USG:launched_at': u'2018-08-16T22:09:40.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-30T17:57:11Z',
                              u'hostId': u'afd50e73c26264d238f90ad731717d11d1b7dd31f04670c5cb2d1b7c',
                              u'OS-EXT-SRV-ATTR:host': u'compute1', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute1.openstack.local',
                              u'name': u'Rocky', u'created': u'2018-08-16T22:09:09Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''},
                             {u'OS-EXT-STS:task_state': None, u'addresses': {u'net3': [
                                 {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:39:02:af', u'version': 4, u'addr': u'10.0.0.6',
                                  u'OS-EXT-IPS:type': u'fixed'}]}, u'links': [{
                                                                                  u'href': u'http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/f2dd3f90-e738-4135-84d4-1a2d30d04929',
                                                                                  u'rel': u'self'}, {
                                                                                  u'href': u'http://10.0.2.15:8774/***************************4bfc1/servers/f2dd3f90-e738-4135-84d4-1a2d30d04929',
                                                                                  u'rel': u'bookmark'}],
                              u'image': {u'id': u'88479e3e-2b19-4432-8eb0-d041e7ed6f8e', u'links': [{
                                                                                                        u'href': u'http://10.0.2.15:8774/***************************4bfc1/images/88479e3e-2b19-4432-8eb0-d041e7ed6f8e',
                                                                                                        u'rel': u'bookmark'}]},
                              u'OS-EXT-STS:vm_state': u'active', u'OS-EXT-SRV-ATTR:instance_name': u'instance-0000001b',
                              u'OS-SRV-USG:launched_at': u'2018-08-16T21:31:03.000000', u'flavor': {u'id': u'10',
                                                                                                    u'links': [{
                                                                                                                   u'href': u'http://10.0.2.15:8774/***************************4bfc1/flavors/10',
                                                                                                                   u'rel': u'bookmark'}]},
                              u'id': u'f2dd3f90-e738-4135-84d4-1a2d30d04929',
                              u'user_id': u'***************************50859', u'OS-DCF:diskConfig': u'AUTO',
                              u'accessIPv4': u'', u'accessIPv6': u'', u'progress': 0, u'OS-EXT-STS:power_state': 1,
                              u'OS-EXT-AZ:availability_zone': u'nova', u'metadata': {}, u'status': u'ACTIVE',
                              u'updated': u'2018-08-20T16:23:01Z',
                              u'hostId': u'afd50e73c26264d238f90ad731717d11d1b7dd31f04670c5cb2d1b7c',
                              u'OS-EXT-SRV-ATTR:host': u'compute1', u'OS-SRV-USG:terminated_at': None,
                              u'key_name': None, u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'compute1.openstack.local',
                              u'name': u'jenga', u'created': u'2018-08-16T21:30:35Z',
                              u'tenant_id': u'***************************3fb11',
                              u'os-extended-volumes:volumes_attached': [], u'config_drive': u''}]}
    elif url == "http://10.0.2.15:5000/v3/projects/***************************73dbe":
        return {u'project': {u'is_domain': False, u'description': u'test project',
                             u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************73dbe'},
                             u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                             u'id': u'***************************73dbe', u'name': u'testProj1'}}
    elif url == "http://10.0.2.15:5000/v3/projects/***************************3fb11":
        return {u'project': {u'is_domain': False, u'description': u'Bootstrap project for initializing the cloud.',
                             u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************3fb11'},
                             u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                             u'id': u'***************************3fb11', u'name': u'admin'}}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/ff2f581c-5d03-4a27-a0ba-f102603fe38f/diagnostics":
        return {u'cpu1_time': 6177810000000, u'tapad123605-18_tx': 0, u'vda_read': 13560832, u'vda_write': 0,
                u'vda_write_req': 0, u'memory-actual': 1048576, u'memory': 1048576, u'tapad123605-18_rx': 17466,
                u'tapad123605-18_rx_errors': 0, u'memory-rss': 146188, u'tapad123605-18_rx_drop': 0,
                u'tapad123605-18_tx_drop': 0, u'cpu0_time': 1876660000000, u'tapad123605-18_rx_packets': 195,
                u'tapad123605-18_tx_packets': 0, u'vda_read_req': 424, u'tapad123605-18_tx_errors': 0,
                u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/acb4197c-f54e-488e-a40a-1b7f59cc9117/diagnostics":
        return {u'cpu1_time': 2682800000000, u'tape690927f-80_rx_drop': 0, u'cpu0_time': 2422550000000,
                u'vda_read': 20160512, u'vda_write': 296960, u'vda_write_req': 84, u'memory-actual': 1048576,
                u'tape690927f-80_tx': 1464, u'memory': 1048576, u'tape690927f-80_tx_packets': 9,
                u'tape690927f-80_tx_drop': 0, u'tape690927f-80_rx_errors': 0, u'tape690927f-80_tx_errors': 0,
                u'memory-rss': 145116, u'tape690927f-80_rx_packets': 185, u'vda_read_req': 878,
                u'tape690927f-80_rx': 16542, u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/b3c8eee3-7e22-4a7c-9745-759073673cbe/diagnostics":
        return {u'cpu1_time': 711180000000, u'vda_read_req': 1154, u'vda_read': 20432896, u'vda_write': 356352,
                u'vda_write_req': 105, u'memory-actual': 1048576, u'tap66a9ffb5-8f_rx': 6306,
                u'tap66a9ffb5-8f_tx': 1464, u'tap66a9ffb5-8f_tx_errors': 0, u'tap66a9ffb5-8f_rx_drop': 0,
                u'tap66a9ffb5-8f_tx_drop': 0, u'memory': 1048576, u'memory-rss': 160832,
                u'tap66a9ffb5-8f_rx_packets': 71, u'cpu0_time': 648410000000, u'tap66a9ffb5-8f_rx_errors': 0,
                u'vda_errors': -1, u'tap66a9ffb5-8f_tx_packets': 9}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/412c79b2-25f2-44d6-8e3b-be4baee11a7f/diagnostics":
        return {u'cpu1_time': 19270000000, u'tap8880f875-12_tx_errors': 0, u'tap8880f875-12_rx_packets': 174,
                u'vda_read': 15403008, u'tap8880f875-12_tx_packets': 0, u'vda_write': 146432, u'vda_write_req': 32,
                u'tap8880f875-12_tx_drop': 0, u'tap8880f875-12_rx': 15564, u'memory-actual': 1048576,
                u'tap8880f875-12_rx_drop': 0, u'cpu0_time': 6915020290000000, u'memory': 1048576, u'memory-rss': 147684,
                u'tap8880f875-12_rx_errors': 0, u'tap8880f875-12_tx': 0, u'vda_errors': -1, u'vda_read_req': 825}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7e622c28-4b12-4a58-8ac2-4a2e854f84eb/diagnostics":
        return {u'cpu1_time': 604250000000, u'memory': 1048576, u'tapb488fc1e-3e_rx_drop': 0,
                u'tapb488fc1e-3e_tx': 1464, u'vda_read': 20446208, u'vda_write': 368640, u'vda_write_req': 105,
                u'memory-actual': 1048576, u'tapb488fc1e-3e_rx_errors': 0, u'tapb488fc1e-3e_rx_packets': 67,
                u'tapb488fc1e-3e_tx_errors': 0, u'memory-rss': 149456, u'tapb488fc1e-3e_tx_packets': 9,
                u'cpu0_time': 556800000000, u'tapb488fc1e-3e_tx_drop': 0, u'tapb488fc1e-3e_rx': 5946,
                u'vda_read_req': 1128, u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/4ceb4c69-a332-4b9d-907b-e99635aae644/diagnostics":
        return {u'cpu1_time': 1417240000000, u'tap69a50430-3b_tx_drop': 0, u'tap69a50430-3b_rx_errors': 0,
                u'tap69a50430-3b_tx': 1464, u'vda_read': 20160512, u'vda_write': 305152, u'vda_write_req': 84,
                u'tap69a50430-3b_tx_errors': 0, u'memory-actual': 1048576, u'tap69a50430-3b_rx_drop': 0,
                u'memory': 1048576, u'vda_errors': -1, u'tap69a50430-3b_rx': 17646, u'tap69a50430-3b_rx_packets': 197,
                u'cpu0_time': 3193240000000, u'memory-rss': 142012, u'vda_read_req': 878,
                u'tap69a50430-3b_tx_packets': 9}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/1cc21586-8d43-40ea-bdc9-6f54a79957b4/diagnostics":
        return {u'cpu1_time': 2342670000000, u'tapc929a75b-94_rx_packets': 199, u'tapc929a75b-94_rx_drop': 0,
                u'tapc929a75b-94_tx': 1464, u'vda_write': 299008, u'vda_write_req': 82, u'tapc929a75b-94_tx_errors': 0,
                u'memory-actual': 1048576, u'memory': 1048576, u'tapc929a75b-94_rx': 17826, u'vda_errors': -1,
                u'tapc929a75b-94_rx_errors': 0, u'tapc929a75b-94_tx_drop': 0, u'cpu0_time': 2124150000000,
                u'memory-rss': 140812, u'vda_read_req': 878, u'vda_read': 20160512, u'tapc929a75b-94_tx_packets': 9}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/836f724f-0028-4dc0-b9bd-e0843d767ca2/diagnostics":
        return {u'cpu1_time': 361230000000, u'memory': 1048576, u'tap73364860-8e_tx_packets': 9,
                u'tap73364860-8e_rx_drop': 0, u'vda_write': 369664, u'vda_write_req': 106, u'tap73364860-8e_rx': 5946,
                u'memory-actual': 1048576, u'tap73364860-8e_tx_errors': 0, u'tap73364860-8e_rx_packets': 67,
                u'vda_errors': -1, u'tap73364860-8e_rx_errors': 0, u'tap73364860-8e_tx': 1464,
                u'cpu0_time': 830250000000, u'memory-rss': 148000, u'vda_read_req': 1161, u'vda_read': 20445184,
                u'tap73364860-8e_tx_drop': 0}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7eaa751c-1e37-4963-a836-0a28bc283a9a/diagnostics":
        return {u'cpu1_time': 2497290000000, u'tapf3e5d7a2-94_rx_drop': 0, u'memory': 1048576, u'vda_read': 15155200,
                u'vda_write': 105472, u'vda_write_req': 28, u'memory-actual': 1048576, u'tapf3e5d7a2-94_tx': 0,
                u'tapf3e5d7a2-94_tx_errors': 0, u'memory-rss': 144460, u'tapf3e5d7a2-94_tx_drop': 0,
                u'tapf3e5d7a2-94_rx_errors': 0, u'cpu0_time': 2512910000000, u'tapf3e5d7a2-94_tx_packets': 0,
                u'tapf3e5d7a2-94_rx_packets': 193, u'vda_read_req': 574, u'tapf3e5d7a2-94_rx': 17286, u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/5357e70e-f12c-4bb7-85a2-b40d642a7e92/diagnostics":
        return {u'cpu1_time': 2487050000000, u'memory': 1048576, u'tapf86369c0-84_rx_packets': 198,
                u'vda_read': 20160512, u'vda_write': 295936, u'vda_write_req': 83, u'memory-actual': 1048576,
                u'tapf86369c0-84_tx_errors': 0, u'cpu0_time': 2242410000000, u'tapf86369c0-84_rx': 17748,
                u'tapf86369c0-84_rx_errors': 0, u'tapf86369c0-84_rx_drop': 0, u'tapf86369c0-84_tx': 1464,
                u'memory-rss': 143992, u'tapf86369c0-84_tx_packets': 9, u'vda_read_req': 878,
                u'tapf86369c0-84_tx_drop': 0, u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/f2dd3f90-e738-4135-84d4-1a2d30d04929/diagnostics":
        return {u'cpu1_time': 2086240000000, u'tap3fd8281c-97_tx_errors': 0, u'tap3fd8281c-97_rx_drop': 0,
                u'vda_write': 316416, u'vda_write_req': 89, u'vda_read': 20153344, u'memory-actual': 1048576,
                u'memory': 1048576, u'tap3fd8281c-97_rx_packets': 207, u'tap3fd8281c-97_tx_packets': 9,
                u'tap3fd8281c-97_tx_drop': 0, u'tap3fd8281c-97_rx': 18522, u'tap3fd8281c-97_rx_errors': 0,
                u'cpu0_time': 4697690000000, u'memory-rss': 146460, u'vda_read_req': 875, u'vda_errors': -1,
                u'tap3fd8281c-97_tx': 1464}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/30888944-fb39-4590-9073-ef977ac1f039/diagnostics":
        return {u'cpu1_time': 2676350000000, u'memory': 1048576, u'tap56f02c54-da_rx_drop': 0, u'vda_read': 20164608,
                u'tap56f02c54-da_tx_errors': 0, u'vda_write': 297984, u'tap56f02c54-da_rx_errors': 0,
                u'tap56f02c54-da_rx_packets': 171, u'memory-actual': 1048576, u'tap56f02c54-da_tx_packets': 9,
                u'vda_write_req': 85, u'tap56f02c54-da_tx': 1464, u'tap56f02c54-da_tx_drop': 0,
                u'cpu0_time': 2406870000000, u'memory-rss': 144728, u'tap56f02c54-da_rx': 15306, u'vda_read_req': 877,
                u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/4d7cb923-788f-4b61-9061-abfc576ecc1a/diagnostics":
        return {u'cpu1_time': 1580310000000, u'tapab9b23ee-c1_rx_errors': 0, u'tapab9b23ee-c1_rx': 15228,
                u'vda_read': 20431872, u'tapab9b23ee-c1_rx_packets': 170, u'vda_write': 373760, u'vda_write_req': 107,
                u'tapab9b23ee-c1_rx_drop': 0, u'memory-actual': 1048576, u'tapab9b23ee-c1_tx': 1464,
                u'tapab9b23ee-c1_tx_drop': 0, u'cpu0_time': 3608370000000, u'memory': 1048576, u'memory-rss': 145892,
                u'tapab9b23ee-c1_tx_errors': 0, u'tapab9b23ee-c1_tx_packets': 9, u'vda_errors': -1,
                u'vda_read_req': 1157}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/2e1ce152-b19d-4c4a-9cc7-0d150fa97a18/diagnostics":
        return {u'cpu1_time': 2966030000000, u'tapcb21dae0-46_rx_errors': 0, u'vda_read_req': 1156,
                u'vda_read': 20458496, u'vda_write': 351232, u'vda_write_req': 108, u'memory-actual': 1048576,
                u'memory': 1048576, u'tapcb21dae0-46_tx_drop': 0, u'memory-rss': 146064,
                u'tapcb21dae0-46_tx_packets': 9, u'tapcb21dae0-46_rx_packets': 172, u'cpu0_time': 2616630000000,
                u'tapcb21dae0-46_rx': 15408, u'tapcb21dae0-46_tx_errors': 0, u'vda_errors': -1,
                u'tapcb21dae0-46_tx': 1464, u'tapcb21dae0-46_rx_drop': 0}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/52561f29-e479-43d7-85de-944d29ef178d/diagnostics":
        return {u'cpu1_time': 1297130000000, u'memory': 1048576, u'tap39a71720-01_tx_drop': 0, u'vda_read': 20160512,
                u'tap39a71720-01_rx_packets': 199, u'vda_write': 297984, u'vda_write_req': 84,
                u'memory-actual': 1048576, u'tap39a71720-01_tx': 1464, u'tap39a71720-01_rx': 17826,
                u'tap39a71720-01_rx_drop': 0, u'tap39a71720-01_rx_errors': 0, u'cpu0_time': 3320700000000,
                u'memory-rss': 142300, u'tap39a71720-01_tx_packets': 9, u'vda_read_req': 878,
                u'tap39a71720-01_tx_errors': 0, u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/1b7a987f-c4fb-4b6b-aad9-3b461df2019d/diagnostics":
        return {u'cpu1_time': 796330000000, u'tap9ac4ed56-d2_tx_drop': 0, u'tap9ac4ed56-d2_rx_errors': 0,
                u'vda_read': 20473856, u'vda_write': 359424, u'vda_write_req': 105, u'memory-actual': 1048576,
                u'memory': 1048576, u'tap9ac4ed56-d2_tx_packets': 9, u'tap9ac4ed56-d2_rx_packets': 71,
                u'tap9ac4ed56-d2_rx_drop': 0, u'tap9ac4ed56-d2_tx': 1464, u'tap9ac4ed56-d2_tx_errors': 0,
                u'cpu0_time': 741940000000, u'memory-rss': 161108, u'vda_read_req': 1171, u'vda_errors': -1,
                u'tap9ac4ed56-d2_rx': 6306}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7324440d-915b-4e12-8b85-ec8c9a524d6c/diagnostics":
        return {u'cpu1_time': 1630220000000, u'tap702092ed-a5_tx': 0, u'tap702092ed-a5_tx_packets': 0,
                u'vda_read': 13560832, u'vda_write': 0, u'vda_write_req': 0, u'memory-actual': 1048576,
                u'memory': 1048576, u'tap702092ed-a5_rx_packets': 66, u'tap702092ed-a5_rx_drop': 0,
                u'memory-rss': 148752, u'tap702092ed-a5_tx_errors': 0, u'tap702092ed-a5_rx': 5844,
                u'cpu0_time': 567940000000, u'tap702092ed-a5_rx_errors': 0, u'tap702092ed-a5_tx_drop': 0,
                u'vda_read_req': 424, u'vda_errors': -1}
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/57030997-f1b5-4f79-9429-8cb285318633/diagnostics":
        return {u'cpu1_time': 1334520000000, u'tap9bff9e73-2f_rx': 13788, u'tap9bff9e73-2f_rx_packets': 154,
                u'vda_read': 20160512, u'vda_write': 307200, u'vda_write_req': 82, u'memory-actual': 1048576,
                u'memory': 1048576, u'tap9bff9e73-2f_tx_packets': 9, u'tap9bff9e73-2f_tx_drop': 0,
                u'memory-rss': 141980, u'tap9bff9e73-2f_rx_errors': 0, u'tap9bff9e73-2f_tx': 1464,
                u'cpu0_time': 3008600000000, u'tap9bff9e73-2f_tx_errors': 0, u'tap9bff9e73-2f_rx_drop': 0,
                u'vda_read_req': 878, u'vda_errors': -1}
    elif url == "http://10.0.2.15:9696/v2.0/networks":
        return {u'networks': [{u'status': u'ACTIVE', u'router:external': True, u'availability_zone_hints': [u'nova'],
                               u'availability_zones': [], u'ipv4_address_scope': None, u'description': u'',
                               u'subnets': [], u'port_security_enabled': False,
                               u'tenant_id': u'***************************3fb11',
                               u'created_at': u'2018-08-16T20:22:34Z', u'tags': [], u'ipv6_address_scope': None,
                               u'updated_at': u'2018-08-16T20:22:34Z', u'is_default': False,
                               u'project_id': u'***************************3fb11', u'revision_number': 4,
                               u'admin_state_up': True, u'shared': False, u'mtu': 1450,
                               u'id': u'2755452c-4fe8-4ba1-9b26-8898665b0958', u'name': u'net2'},
                              {u'status': u'ACTIVE', u'router:external': False, u'availability_zone_hints': [],
                               u'availability_zones': [u'nova'], u'ipv4_address_scope': None, u'description': u'',
                               u'subnets': [u'22eee592-35c1-4edd-9d8b-eaafd4ce326c'], u'port_security_enabled': True,
                               u'tenant_id': u'***************************3fb11',
                               u'created_at': u'2018-08-16T21:13:01Z', u'tags': [], u'ipv6_address_scope': None,
                               u'updated_at': u'2018-08-16T21:13:32Z',
                               u'project_id': u'***************************3fb11', u'revision_number': 5,
                               u'admin_state_up': True, u'shared': True, u'mtu': 1450,
                               u'id': u'2fad0a98-4ba9-44f4-8f81-87c31c5eab10', u'name': u'net3'}]}
    elif url == "http://10.0.2.15:9696/v2.0/networks/2fad0a98-4ba9-44f4-8f81-87c31c5eab10":
        return {u'network': {u'status': u'ACTIVE', u'router:external': False, u'availability_zone_hints': [],
                             u'availability_zones': [u'nova'], u'ipv4_address_scope': None, u'description': u'',
                             u'subnets': [u'22eee592-35c1-4edd-9d8b-eaafd4ce326c'], u'port_security_enabled': True,
                             u'tenant_id': u'***************************3fb11', u'created_at': u'2018-08-16T21:13:01Z',
                             u'tags': [], u'ipv6_address_scope': None, u'updated_at': u'2018-08-16T21:13:32Z',
                             u'project_id': u'***************************3fb11', u'revision_number': 5,
                             u'admin_state_up': True, u'shared': True, u'mtu': 1450,
                             u'id': u'2fad0a98-4ba9-44f4-8f81-87c31c5eab10', u'name': u'net3'}}
    elif url == "http://10.0.2.15:9696/v2.0/networks/2755452c-4fe8-4ba1-9b26-8898665b0958":
        return {u'network': {u'status': u'ACTIVE', u'router:external': True, u'availability_zone_hints': [u'nova'],
                             u'availability_zones': [], u'ipv4_address_scope': None, u'description': u'',
                             u'subnets': [], u'port_security_enabled': False,
                             u'tenant_id': u'***************************3fb11', u'created_at': u'2018-08-16T20:22:34Z',
                             u'tags': [], u'ipv6_address_scope': None, u'updated_at': u'2018-08-16T20:22:34Z',
                             u'is_default': False, u'project_id': u'***************************3fb11',
                             u'revision_number': 4, u'admin_state_up': True, u'shared': False, u'mtu': 1450,
                             u'id': u'2755452c-4fe8-4ba1-9b26-8898665b0958', u'name': u'net2'}}


AUTH_PROJECTS_RESPONSE = [{u'is_domain': False, u'description': u'Keystone Identity Service',
                           u'links': {u'self': u'http://10.0.2.15:5000/v3/projects/***************************4bfc1'},
                           u'enabled': True, u'domain_id': u'default', u'parent_id': u'default',
                           u'id': u'***************************4bfc1', u'name': u'service'}]

AUTH_TOKENS_RESPONSE = {u'token': {u'is_domain': False, u'methods': [u'token', u'password'], u'roles': [
    {u'id': u'***************************91953', u'name': u'admin_read_only'}],
                                   u'expires_at': u'2018-11-23T03:34:53.000000Z',
                                   u'project': {u'domain': {u'id': u'default', u'name': u'Default'},
                                                u'id': u'***************************4bfc1', u'name': u'service'},
                                   u'catalog': [{u'endpoints': [
                                       {u'url': u'http://10.0.2.15:9292', u'interface': u'internal',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************b4841'},
                                       {u'url': u'http://10.0.2.15:9292', u'interface': u'admin',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************a0f45'},
                                       {u'url': u'http://10.0.3.10:9292', u'interface': u'public',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************0e5c2'}], u'type': u'image',
                                                 u'id': u'***************************846cb', u'name': u'glance'}, {
                                                    u'endpoints': [{
                                                                       u'url': u'http://10.0.3.229:8774/v2.1/***************************4bfc1',
                                                                       u'interface': u'public', u'region': u'RegionOne',
                                                                       u'region_id': u'RegionOne',
                                                                       u'id': u'***************************9ed89'}, {
                                                                       u'url': u'http://10.0.2.15:8774/v2.1/***************************4bfc1',
                                                                       u'interface': u'admin', u'region': u'RegionOne',
                                                                       u'region_id': u'RegionOne',
                                                                       u'id': u'***************************e47a2'}, {
                                                                       u'url': u'http://10.0.2.15:8774/v2.1/***************************4bfc1',
                                                                       u'interface': u'internal',
                                                                       u'region': u'RegionOne',
                                                                       u'region_id': u'RegionOne',
                                                                       u'id': u'***************************b016b'}, {
                                                                       u'url': u'http://10.0.2.15:8774/v2.1/***************************4bfc1',
                                                                       u'interface': u'public', u'region': None,
                                                                       u'region_id': None,
                                                                       u'id': u'***************************d7802'}],
                                                    u'type': u'compute', u'id': u'***************************05d1f',
                                                    u'name': u'nova'}, {u'endpoints': [
                                       {u'url': u'http://10.0.2.15:9696', u'interface': u'internal',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************abf66'},
                                       {u'url': u'http://10.0.2.15:9696', u'interface': u'admin',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************8d1ca'},
                                       {u'url': u'http://10.0.2.15:9696', u'interface': u'public', u'region': None,
                                        u'region_id': None, u'id': u'***************************64be0'}],
                                                                        u'type': u'network',
                                                                        u'id': u'***************************9a6f4',
                                                                        u'name': u'neutron'}, {u'endpoints': [
                                       {u'url': u'http://10.0.3.111:8776/v3/***************************4bfc1',
                                        u'interface': u'public', u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************89f4a'},
                                       {u'url': u'http://10.0.2.15:8776/v3/***************************4bfc1',
                                        u'interface': u'internal', u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************d9fb1'},
                                       {u'url': u'http://10.0.2.15:8776/v3/***************************4bfc1',
                                        u'interface': u'admin', u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************1b330'}], u'type': u'volumev3',
                                                                                               u'id': u'***************************3ac57',
                                                                                               u'name': u'cinderv3'}, {
                                                    u'endpoints': [{
                                                                       u'url': u'http://10.0.3.111:8776/v1/***************************4bfc1',
                                                                       u'interface': u'public', u'region': u'RegionOne',
                                                                       u'region_id': u'RegionOne',
                                                                       u'id': u'***************************2452f'}, {
                                                                       u'url': u'http://10.0.2.15:8776/v1/***************************4bfc1',
                                                                       u'interface': u'admin', u'region': u'RegionOne',
                                                                       u'region_id': u'RegionOne',
                                                                       u'id': u'***************************8239f'}, {
                                                                       u'url': u'http://10.0.2.15:8776/v1/***************************4bfc1',
                                                                       u'interface': u'internal',
                                                                       u'region': u'RegionOne',
                                                                       u'region_id': u'RegionOne',
                                                                       u'id': u'***************************7caa1'}],
                                                    u'type': u'volume', u'id': u'***************************e7e16',
                                                    u'name': u'cinder'}, {u'endpoints': [
                                       {u'url': u'http://10.0.3.44:5000/v3', u'interface': u'public',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************a23db'},
                                       {u'url': u'http://10.0.2.15:5000/v3', u'interface': u'internal',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************9febe'},
                                       {u'url': u'http://10.0.2.15:35357/v3', u'interface': u'admin',
                                        u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************f0cdb'}], u'type': u'identity',
                                                                          u'id': u'***************************17167',
                                                                          u'name': u'keystone'}, {u'endpoints': [
                                       {u'url': u'http://10.0.2.15:8776/v2/***************************4bfc1',
                                        u'interface': u'admin', u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************0530c'},
                                       {u'url': u'http://10.0.3.111:8776/v2/***************************4bfc1',
                                        u'interface': u'public', u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************9b358'},
                                       {u'url': u'http://10.0.2.15:8776/v2/***************************4bfc1',
                                        u'interface': u'internal', u'region': u'RegionOne', u'region_id': u'RegionOne',
                                        u'id': u'***************************58920'}], u'type': u'volumev2',
                                                                                                  u'id': u'***************************cfa2d',
                                                                                                  u'name': u'cinderv2'}],
                                   u'user': {u'domain': {u'id': u'default', u'name': u'Default'},
                                             u'id': u'***************************bde1b', u'name': u'datadog_os_user'},
                                   u'audit_ids': [u'qdcm2BRVSa26oSDpZuclVA', u'8VJwugdcQrmRgu2NtKwMmA'],
                                   u'issued_at': u'2018-11-22T15:34:54.000000Z'}}

MOCK_CONFIG = {
    'init_config': {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
    },
    'instances': [
        {
            'name': 'test_name', 'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}}
        }
    ]
}


class MockHTTPResponse(object):
    def __init__(self, response_dict, headers):
        self.response_dict = response_dict
        self.headers = headers

    def json(self):
        return self.response_dict


def test_check(aggregator):
    instance = MOCK_CONFIG["instances"][0]
    init_config = MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])

    mock_http_response = copy.deepcopy(AUTH_TOKENS_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=AUTH_PROJECTS_RESPONSE):
            with mock.patch('datadog_checks.openstack_controller.openstack_controller.OpenStackControllerCheck._make_request_with_auth_fallback',
                            side_effect=make_request_responses):
                check.check(MOCK_CONFIG['instances'][0])

                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')

                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_rx', value=17286.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_tx', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality', value=10.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_tx_packets', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_tx', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_rx', value=16542.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=1.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=1.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=20.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_rx', value=15564.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_tx_packets', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_rx_packets', value=170.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_rx', value=6306.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_tx', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=17408.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=1024.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_rx', value=15408.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_rx', value=5946.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=3886.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=5934.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=3886.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=5934.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=3886.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=5934.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_rx_packets', value=207.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_rx_packets', value=67.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2422550000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=648410000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=6915020290000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=830250000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3008600000000.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=741940000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2406870000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3193240000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2616630000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3608370000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2124150000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=556800000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=4697690000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3320700000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=1876660000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2512910000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=567940000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2242410000000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')

                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_rx_packets', value=67.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_rx_packets', value=193.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=4.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=0.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=4.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=0.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=4.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=0.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=2.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=0.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=2.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=0.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=2.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=0.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=17.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=1.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_rx_packets', value=71.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_rx', value=15306.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=26.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=46.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=26.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=46.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=26.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=46.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=22.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=2.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=22.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=2.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=22.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=2.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'], hostname='')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_rx_packets', value=195.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_tx_packets', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_rx_packets', value=199.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_rx_packets', value=71.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_rx', value=5946.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_rx_packets', value=198.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_rx_packets', value=172.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=34.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=2.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_rx', value=17826.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=296960.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=356352.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=146432.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=369664.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=307200.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=359424.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=297984.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=305152.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=351232.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=373760.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=299008.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=368640.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=316416.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=297984.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=105472.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.vda_write', value=295936.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_rx', value=17466.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tapab9b23ee_c1_rx', value=15228.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_rx_packets', value=66.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_rx', value=18522.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_rx_packets', value=197.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1154.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=825.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1161.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1171.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=877.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1156.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1157.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1128.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=875.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=424.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=574.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=424.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20432896.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=15403008.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20445184.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20473856.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20164608.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20458496.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20431872.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20446208.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20153344.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=13560832.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=15155200.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=13560832.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')

                aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_tx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_rx', value=6306.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=10.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_rx', value=5844.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_rx_packets', value=154.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=14.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=-2.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=38.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=2.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=14.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=37.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=3.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=13.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=3.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.disk_available_least', value=3.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tapf3e5d7a2_94_tx', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=84.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=105.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=32.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=106.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=82.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=105.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=85.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=84.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=108.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=107.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=82.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=105.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=89.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=84.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=28.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.vda_write_req', value=83.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=145116.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=160832.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=147684.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=148000.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=141980.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=161108.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=144728.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=142012.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=146064.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=145892.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                               'availability_zone:nova'],
                                         hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=140812.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=149456.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=146460.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                               'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=142300.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=146188.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=144460.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                               'availability_zone:nova'],
                                         hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=148752.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                               'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.memory_rss', value=143992.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_rx_packets', value=185.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.tapad123605_18_tx_packets', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                               'availability_zone:nova'],
                                         hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_rx', value=13788.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_rx_packets', value=199.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=4096.0,
                                         tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                         tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=2048.0,
                                         tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                         tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=4096.0,
                                         tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=2048.0,
                                         tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                         tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=4096.0,
                                         tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=2048.0,
                                         tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                         tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                               'virt_type:QEMU', 'status:enabled'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.tape690927f_80_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                               'availability_zone:nova'],
                                         hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_rx', value=17748.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                         tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                         tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                         tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                         tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                         tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                         tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                         hostname='')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.tap66a9ffb5_8f_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                               'availability_zone:nova'],
                                         hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
                aggregator.assert_metric('openstack.nova.server.tap9ac4ed56_d2_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local',
                                               'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                         hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
                aggregator.assert_metric('openstack.nova.server.tapf86369c0_84_rx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                               'availability_zone:nova'],
                                         hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
                aggregator.assert_metric('openstack.nova.server.tap9bff9e73_2f_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:testProj1',
                                               'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                               'availability_zone:nova'],
                                         hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
                aggregator.assert_metric('openstack.nova.server.tap39a71720_01_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                               'availability_zone:nova'],
                                         hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
                aggregator.assert_metric('openstack.nova.server.tapc929a75b_94_rx', value=17826.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                               'availability_zone:nova'],
                                         hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
                aggregator.assert_metric('openstack.nova.server.tapcb21dae0_46_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                               'availability_zone:nova'],
                                         hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                               'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.tap8880f875_12_rx_packets', value=174.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                               'availability_zone:nova'],
                                         hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
                aggregator.assert_metric('openstack.nova.server.tap73364860_8e_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local',
                                               'server_name:finalDestination-8', 'availability_zone:nova'],
                                         hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
                aggregator.assert_metric('openstack.nova.server.tap3fd8281c_97_tx', value=1464.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute1.openstack.local',
                                               'server_name:jenga', 'availability_zone:nova'],
                                         hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_rx', value=17646.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local',
                                               'server_name:moarserver-13', 'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.tap702092ed_a5_rx_errors', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local',
                                               'server_name:blacklist', 'availability_zone:nova'],
                                         hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
                aggregator.assert_metric('openstack.nova.server.tap69a50430_3b_tx_drop', value=0.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                               'availability_zone:nova'],
                                         hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
                aggregator.assert_metric('openstack.nova.server.tap56f02c54_da_rx_packets', value=171.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                               'availability_zone:nova'],
                                         hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
                aggregator.assert_metric('openstack.nova.server.tapb488fc1e_3e_tx_packets', value=9.0,
                                         tags=['nova_managed_server', 'project_name:admin',
                                               'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                               'availability_zone:nova'],
                                         hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()