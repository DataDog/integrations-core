# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import struct

from pymqi import PCFExecute, CMQCFC, CFH, MQMIError, CFST, CFSL, CFIN, CFIL, MQOpts, MQLONG_TYPE, CFBS


class CFIL64(MQOpts):
    """ Construct an MQCFIL Structure with default values as per MQI.
    The default values may be overridden by the optional keyword arguments 'kw'.
    """
    def __init__(self, **kw):
        # types: (Dict[str, Any]) -> None
        values = kw.pop('Values', [])
        count = kw.pop('Count', len(values))
        MQLONG_TYPE_64 = 'l'

        opts = [['Type', CMQCFC.MQCFT_INTEGER64_LIST, MQLONG_TYPE],
                ['StrucLength', CMQCFC.MQCFIL64_STRUC_LENGTH_FIXED + 8 * count, MQLONG_TYPE], # Check python 2
                ['Parameter', 0, MQLONG_TYPE],
                ['Count', count, MQLONG_TYPE],
                ['Values', values, MQLONG_TYPE_64, count],
               ]
        super(CFIL64, self).__init__(tuple(opts), **kw)

class CustomPCFExecute(PCFExecute):

    @staticmethod
    def unpack(message): # type: (bytes) -> dict
        """Unpack PCF message to dictionary
        """

        mqcfh = CFH(Version=CMQCFC.MQCFH_VERSION_1)
        mqcfh.unpack(message[:CMQCFC.MQCFH_STRUC_LENGTH])

        if mqcfh.Version != CMQCFC.MQCFH_VERSION_1:
            mqcfh = CFH(Version=mqcfh.Version)
            mqcfh.unpack(message[:CMQCFC.MQCFH_STRUC_LENGTH])

        if mqcfh.CompCode:
            raise MQMIError(mqcfh.CompCode, mqcfh.Reason)

        # print("mqcfh", mqcfh)
        # print("mqcfh.ParameterCount", mqcfh.ParameterCount)
        # print("mqcfh.Command", mqcfh.Command)
        res = {}
        index = mqcfh.ParameterCount
        cursor = CMQCFC.MQCFH_STRUC_LENGTH
        parameter = None # type: Optional[MQOpts]
        while (index > 0):
            if message[cursor] == CMQCFC.MQCFT_STRING:
                parameter = CFST()
                parameter.unpack(message[cursor:cursor + CMQCFC.MQCFST_STRUC_LENGTH_FIXED])
                if parameter.StringLength > 1:
                    parameter = CFST(StringLength=parameter.StringLength)
                    parameter.unpack(message[cursor:cursor + parameter.StrucLength])
                value = parameter.String
            elif message[cursor] == CMQCFC.MQCFT_STRING_LIST:
                parameter = CFSL()
                parameter.unpack(message[cursor:cursor + CMQCFC.MQCFSL_STRUC_LENGTH_FIXED])
                if parameter.StringLength > 1:
                    parameter = CFSL(StringLength=parameter.StringLength,
                                     Count=parameter.Count,
                                     StrucLength=parameter.StrucLength)
                    parameter.unpack(message[cursor:cursor + parameter.StrucLength])
                value = parameter.Strings
            elif message[cursor] == CMQCFC.MQCFT_INTEGER:
                parameter = CFIN()
                parameter.unpack(message[cursor:cursor + CMQCFC.MQCFIN_STRUC_LENGTH])
                value = parameter.Value
            elif message[cursor] == CMQCFC.MQCFT_INTEGER_LIST:
                parameter = CFIL()
                parameter.unpack(message[cursor:cursor + CMQCFC.MQCFIL_STRUC_LENGTH_FIXED])
                if parameter.Count > 0:
                    parameter = CFIL(Count=parameter.Count,
                                     StrucLength=parameter.StrucLength)
                    parameter.unpack(message[cursor:cursor + parameter.StrucLength])
                value = parameter.Values
            elif message[cursor] == CMQCFC.MQCFT_INTEGER64_LIST:
                parameter = CFIL64()
                parameter.unpack(message[cursor:cursor + CMQCFC.MQCFIL64_STRUC_LENGTH_FIXED])
                print(parameter)
                print(res)
                if parameter.Count > 0:
                    parameter = CFIL64(Count=parameter.Count,
                                     StrucLength=parameter.StrucLength)
                    parameter.unpack(message[cursor:cursor + parameter.StrucLength])
                value = parameter.Values
            elif message[cursor] == CMQCFC.MQCFT_GROUP:
                1/0
            elif message[cursor] == CMQCFC.MQCFT_BYTE_STRING:
                parameter = CFBS()
                parameter.unpack(message[cursor:cursor + CMQCFC.MQCFBS_STRUC_LENGTH_FIXED])
                if parameter.StringLength > 1:
                    parameter = CFBS(StringLength=parameter.StringLength)
                    parameter.unpack(message[cursor:cursor + parameter.StrucLength])
                value = parameter.String
            else:
                pcf_type = struct.unpack(MQLONG_TYPE, message[cursor:cursor + 4])
                raise NotImplementedError('Unpack for type ({}) not implemented'.format(pcf_type))
            index -= 1
            cursor += parameter.StrucLength
            res[parameter.Parameter] = value

        return res, mqcfh.Control


    @staticmethod
    def unpack_header(message):
        mqcfh = CFH(Version=CMQCFC.MQCFH_VERSION_1)
        mqcfh.unpack(message[:CMQCFC.MQCFH_STRUC_LENGTH])

        if mqcfh.Version != CMQCFC.MQCFH_VERSION_1:
            mqcfh = CFH(Version=mqcfh.Version)
            mqcfh.unpack(message[:CMQCFC.MQCFH_STRUC_LENGTH])

        if mqcfh.CompCode:
            raise MQMIError(mqcfh.CompCode, mqcfh.Reason)

        return mqcfh

