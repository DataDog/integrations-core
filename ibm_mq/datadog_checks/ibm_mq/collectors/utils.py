# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Dict, Optional, Union

import pymqi
from pymqi import (
    CFBS,
    CFH,
    CFIL,
    CFIN,
    CFST,
    CMQC,
    CMQCFC,
    GMO,
    MD,
    PMO,
    ByteString,
    MQMIError,
    MQOpts,
    PCFExecute,
    Queue,
    is_unicode,
)

INTEGER64_TYPE = 'q'


def unpack_header(message):  # type: (bytes) -> dict
    """Unpack PCF message to dictionary
    """
    mqcfh = CFH(Version=CMQCFC.MQCFH_VERSION_1)
    mqcfh.unpack(message[: CMQCFC.MQCFH_STRUC_LENGTH])

    if mqcfh.Version != CMQCFC.MQCFH_VERSION_1:
        mqcfh = CFH(Version=mqcfh.Version)
        mqcfh.unpack(message[: CMQCFC.MQCFH_STRUC_LENGTH])

    if mqcfh.CompCode:
        raise MQMIError(mqcfh.CompCode, mqcfh.Reason)

    return mqcfh


class CFIL64(MQOpts):
    """ Construct an MQCFIL64 Structure with default values as per MQI.
    The default values may be overridden by the optional keyword arguments 'kw'.
    """

    def __init__(self, **kw):
        # types: (Dict[str, Any]) -> None
        values = kw.pop('Values', [])
        count = kw.pop('Count', len(values))

        opts = [
            ['Type', CMQCFC.MQCFT_INTEGER64_LIST, pymqi.MQLONG_TYPE],
            ['StrucLength', CMQCFC.MQCFIL64_STRUC_LENGTH_FIXED + 8 * count, pymqi.MQLONG_TYPE],
            ['Parameter', 0, pymqi.MQLONG_TYPE],
            ['Count', count, pymqi.MQLONG_TYPE],
            ['Values', values, INTEGER64_TYPE, count],
        ]
        super(CFIL64, self).__init__(tuple(opts), **kw)


class CFGR(MQOpts):
    """ Construct an MQCFGR Structure with default values as per MQI.
    The default values may be overridden by the optional keyword arguments 'kw'.
    """

    def __init__(self, **kw):
        # types: (Dict[str, Any]) -> None
        count = kw.pop('ParameterCount', 0)

        opts = [
            ['Type', CMQCFC.MQCFT_GROUP, pymqi.MQLONG_TYPE],
            ['StrucLength', CMQCFC.MQCFGR_STRUC_LENGTH, pymqi.MQLONG_TYPE],
            ['Parameter', 0, pymqi.MQLONG_TYPE],
            ['ParameterCount', count, pymqi.MQLONG_TYPE],
        ]
        super(CFGR, self).__init__(tuple(opts), **kw)


class CFIN64(MQOpts):
    """ Construct an MQCFIN64 Structure with default values as per MQI.
    The default values may be overridden by the optional keyword arguments 'kw'.
    """

    def __init__(self, **kw):
        # types: (Dict[str, Any]) -> None -> None

        opts = [
            ['Type', CMQCFC.MQCFT_INTEGER64, pymqi.MQLONG_TYPE],
            ['StrucLength', CMQCFC.MQCFIN64_STRUC_LENGTH, pymqi.MQLONG_TYPE],
            ['Parameter', 0, pymqi.MQLONG_TYPE],
            ['Value', 0, INTEGER64_TYPE],
        ]
        super(CFIN64, self).__init__(tuple(opts), **kw)


class CustomPCFExecute(PCFExecute):
    @staticmethod
    def unpack(message):  # type: (bytes) -> dict
        """Unpack PCF message to dictionary
        """
        import struct

        from pymqi import CMQCFC, CFH, MQMIError, MQLONG_TYPE, CFST, CFSL, CFIN, CFIL, CFBS

        mqcfh = CFH(Version=CMQCFC.MQCFH_VERSION_1)
        mqcfh.unpack(message[: CMQCFC.MQCFH_STRUC_LENGTH])

        if mqcfh.Version != CMQCFC.MQCFH_VERSION_1:
            mqcfh = CFH(Version=mqcfh.Version)
            mqcfh.unpack(message[: CMQCFC.MQCFH_STRUC_LENGTH])

        if mqcfh.CompCode:
            raise MQMIError(mqcfh.CompCode, mqcfh.Reason)

        res = {}  # type: Dict[str, Union[int, str, bool, Dict]]
        index = mqcfh.ParameterCount
        cursor = CMQCFC.MQCFH_STRUC_LENGTH
        parameter = None  # type: Optional[MQOpts]
        group = None  # type: Union[None, Dict[str, Union[str, int, bool]]]
        group_count = 0

        while index > 0:
            parameter_type = struct.unpack(MQLONG_TYPE, message[cursor : cursor + 4])[0]
            if group_count == 0:
                group = None
            if group is not None:
                group_count -= 1
            if parameter_type == CMQCFC.MQCFT_STRING:
                parameter = CFST()
                parameter.unpack(message[cursor : cursor + CMQCFC.MQCFST_STRUC_LENGTH_FIXED])
                if parameter.StringLength > 1:
                    parameter = CFST(StringLength=parameter.StringLength)
                    parameter.unpack(message[cursor : cursor + parameter.StrucLength])
                value = parameter.String
            elif parameter_type == CMQCFC.MQCFT_STRING_LIST:
                parameter = CFSL()
                parameter.unpack(message[cursor : cursor + CMQCFC.MQCFSL_STRUC_LENGTH_FIXED])
                if parameter.StringLength > 1:
                    parameter = CFSL(
                        StringLength=parameter.StringLength, Count=parameter.Count, StrucLength=parameter.StrucLength
                    )
                    parameter.unpack(message[cursor : cursor + parameter.StrucLength])
                value = parameter.Strings
            elif parameter_type == CMQCFC.MQCFT_INTEGER:
                parameter = CFIN()
                parameter.unpack(message[cursor : cursor + CMQCFC.MQCFIN_STRUC_LENGTH])
                value = parameter.Value
            elif parameter_type == CMQCFC.MQCFT_INTEGER64:
                parameter = CFIN64()
                parameter.unpack(message[cursor : cursor + CMQCFC.MQCFIN64_STRUC_LENGTH])
                value = parameter.Value
            elif parameter_type == CMQCFC.MQCFT_INTEGER_LIST:
                parameter = CFIL()
                parameter.unpack(message[cursor : cursor + CMQCFC.MQCFIL_STRUC_LENGTH_FIXED])
                if parameter.Count > 0:
                    parameter = CFIL(Count=parameter.Count, StrucLength=parameter.StrucLength)
                    parameter.unpack(message[cursor : cursor + parameter.StrucLength])
                value = parameter.Values
            elif parameter_type == CMQCFC.MQCFT_INTEGER64_LIST:
                parameter = CFIL64()
                parameter.unpack(message[cursor : cursor + CMQCFC.MQCFIL64_STRUC_LENGTH_FIXED])
                if parameter.Count > 0:
                    parameter = CFIL64(Count=parameter.Count, StrucLength=parameter.StrucLength)
                    parameter.unpack(message[cursor : cursor + parameter.StrucLength])
                value = parameter.Values
            elif parameter_type == CMQCFC.MQCFT_GROUP:
                parameter = CFGR()
                parameter.unpack(message[cursor : cursor + parameter.StrucLength])
                group_count = parameter.ParameterCount
                index += group_count
                group = {}
                res[parameter.Parameter] = res.get(parameter.Parameter, [])  # type: ignore
                res[parameter.Parameter].append(group)  # type: ignore
            elif parameter_type == CMQCFC.MQCFT_BYTE_STRING:
                parameter = CFBS()
                parameter.unpack(message[cursor : cursor + CMQCFC.MQCFBS_STRUC_LENGTH_FIXED])
                if parameter.StringLength > 1:
                    parameter = CFBS(StringLength=parameter.StringLength)
                    parameter.unpack(message[cursor : cursor + parameter.StrucLength])
                value = parameter.String
            else:
                pcf_type = struct.unpack(MQLONG_TYPE, message[cursor : cursor + 4])
                raise NotImplementedError('Unpack for type ({}) not implemented'.format(pcf_type))
            index -= 1
            cursor += parameter.StrucLength
            if parameter.Type == CMQCFC.MQCFT_GROUP:
                continue
            if group is not None:
                group[parameter.Parameter] = value
            else:
                res[parameter.Parameter] = value

        return res, mqcfh  # type: ignore


#
# This piece of magic shamelessly plagiarised from xmlrpclib.py. It
# works a bit like a C++ STL functor.
#
class _Method:
    def __init__(self, pcf, name):
        # types: (PCFExecute, str) -> None
        self.__pcf = pcf
        self.__name = name

    def __getattr__(self, name):
        # types: (str) -> _Method
        return _Method(self.__pcf, '%s.%s' % (self.__name, name))

    def __call__(self, *args):
        # types: (Unions[dict, list, _Filter]) -> list
        if self.__name[0:7] == 'CMQCFC.':
            self.__name = self.__name[7:]
        if self.__pcf.qm:
            bytes_encoding = self.__pcf.bytes_encoding
            _ = self.__pcf.qm.getHandle()
        else:
            bytes_encoding = 'utf8'
            _ = self.__pcf.getHandle()

        len_args = len(args)

        if len_args == 2:
            args_dict, filters = args

        elif len_args == 1:
            args_dict, filters = args[0], []

        else:
            args_dict, filters = {}, []

        mqcfh = CFH(
            Version=CMQCFC.MQCFH_VERSION_3,
            Command=CMQCFC.__dict__[self.__name],
            Type=CMQCFC.MQCFT_COMMAND_XR,
            ParameterCount=len(args_dict) + len(filters),
        )
        message = mqcfh.pack()

        if args_dict:
            if isinstance(args_dict, dict):
                for key, value in args_dict.items():
                    if isinstance(value, (str, bytes)):
                        if is_unicode(value):
                            value = value.encode(bytes_encoding)
                        parameter = CFST(Parameter=key, String=value)
                    elif isinstance(value, ByteString):
                        parameter = CFBS(Parameter=key, String=value.value.encode(bytes_encoding))
                    elif isinstance(value, int):
                        # Backward compatibility for MQAI behaviour
                        # for single value instead of list
                        is_list = False
                        for item in CMQCFC.__dict__:
                            if (
                                (item[:7] == 'MQIACF_' or item[:7] == 'MQIACH_')
                                and item[-6:] == '_ATTRS'
                                and CMQCFC.__dict__[item] == key
                            ):
                                is_list = True
                                break
                        if not is_list:
                            parameter = CFIN(Parameter=key, Value=value)
                        else:
                            parameter = CFIL(Parameter=key, Values=[value])
                    elif isinstance(value, list) and isinstance(value[0], int):
                        parameter = CFIL(Parameter=key, Values=value)

                    message = message + parameter.pack()
            elif isinstance(args_dict, list):
                for parameter in args_dict:
                    message = message + parameter.pack()

        if filters:
            for pcf_filter in filters:
                if isinstance(pcf_filter, pymqi._Filter):
                    if pcf_filter._pymqi_filter_type == 'string':
                        pcf_filter = pymqi.CFSF(
                            Parameter=pcf_filter.selector, Operator=pcf_filter.operator, FilterValue=pcf_filter.value
                        )
                    elif pcf_filter._pymqi_filter_type == 'integer':
                        pcf_filter = pymqi.CFIF(
                            Parameter=pcf_filter.selector, Operator=pcf_filter.operator, FilterValue=pcf_filter.value
                        )

                message = message + pcf_filter.pack()

        command_queue = Queue(self.__pcf.qm, self.__pcf._command_queue_name, CMQC.MQOO_OUTPUT)

        put_md = MD(
            Format=CMQC.MQFMT_ADMIN,
            MsgType=CMQC.MQMT_REQUEST,
            ReplyToQ=self.__pcf._reply_queue_name,
            Feedback=CMQC.MQFB_NONE,
            Expiry=self.__pcf.response_wait_interval,
            Report=CMQC.MQRO_PASS_DISCARD_AND_EXPIRY | CMQC.MQRO_DISCARD_MSG,
        )
        put_opts = PMO(Options=CMQC.MQPMO_NO_SYNCPOINT)

        command_queue.put(message, put_md, put_opts)
        command_queue.close()

        gmo_options = CMQC.MQGMO_NO_SYNCPOINT + CMQC.MQGMO_FAIL_IF_QUIESCING + CMQC.MQGMO_WAIT

        if self.__pcf.convert:
            gmo_options = gmo_options + CMQC.MQGMO_CONVERT

        get_opts = GMO(
            Options=gmo_options,
            Version=CMQC.MQGMO_VERSION_2,
            MatchOptions=CMQC.MQMO_MATCH_CORREL_ID,
            WaitInterval=self.__pcf.response_wait_interval,
        )
        get_md = MD(CorrelId=put_md.MsgId)

        ress = []
        while True:
            message = self.__pcf._reply_queue.get(None, get_md, get_opts)
            res, header = self.__pcf.unpack(message)

            ress.append(res)

            if header.Control == CMQCFC.MQCFC_LAST:
                break

        return ress


pymqi._Method = _Method
