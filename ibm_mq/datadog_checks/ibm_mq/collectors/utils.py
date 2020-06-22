# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pymqi import CMQCFC, CFH, MQMIError


def unpack_header(message): # type: (bytes) -> dict
    """Unpack PCF message to dictionary
    """
    mqcfh = CFH(Version=CMQCFC.MQCFH_VERSION_1)
    mqcfh.unpack(message[:CMQCFC.MQCFH_STRUC_LENGTH])

    if mqcfh.Version != CMQCFC.MQCFH_VERSION_1:
        mqcfh = CFH(Version=mqcfh.Version)
        mqcfh.unpack(message[:CMQCFC.MQCFH_STRUC_LENGTH])

    if mqcfh.CompCode:
        raise MQMIError(mqcfh.CompCode, mqcfh.Reason)

    return mqcfh


