
https://community.ibm.com/community/user/imwuc/viewdocument/parsing-mq-event-messages-as-python?CommunityKey=183ec850-4947-49c8-9a2e-8e7c7fc46c64&tab=librarydocuments

```
ALTER QMGR ACCTINT(60) ACCTMQI(ON) ACCTQ(ON)
ALTER QMGR STATINT(30) STATMQI(ON) STATQ(ON)
```

## Accounting messages
https://www.ibm.com/support/knowledgecenter/SSFKSJ_9.0.0/com.ibm.mq.mon.doc/q037250_.htm


## Statistics messages
https://www.ibm.com/support/knowledgecenter/SSFKSJ_9.0.0/com.ibm.mq.mon.doc/q037320_.htm

Attributes matches with `SYSTEM.ADMIN.STATISTICS.QUEUE.Statistics_Queue.json`:
- https://www.ibm.com/support/knowledgecenter/SSGRP3_2.3.0.1/doc/iwd/tivoli_agent_MQS/attr_qmq_stat.html

Attributes matches with `SYSTEM.ADMIN.STATISTICS.QUEUE.Statistics_MQI.json`: 
- https://www.ibm.com/support/knowledgecenter/SSGRP3_2.3.0.1/doc/iwd/tivoli_agent_MQS/attr_qmmqistat.html

```c

 typedef struct tagMQMD1 MQMD1;
 typedef MQMD1 MQPOINTER PMQMD1;

 struct tagMQMD1 {
   MQCHAR4   StrucId;           /* Structure identifier */
   MQLONG    Version;           /* Structure version number */
   MQLONG    Report;            /* Options for report messages */
   MQLONG    MsgType;           /* Message type */
   MQLONG    Expiry;            /* Message lifetime */
   MQLONG    Feedback;          /* Feedback or reason code */
   MQLONG    Encoding;          /* Numeric encoding of message data */
   MQLONG    CodedCharSetId;    /* Character set identifier of */
                                /* message data */
   MQCHAR8   Format;            /* Format name of message data */
   MQLONG    Priority;          /* Message priority */
   MQLONG    Persistence;       /* Message persistence */
   MQBYTE24  MsgId;             /* Message identifier */
   MQBYTE24  CorrelId;          /* Correlation identifier */
   MQLONG    BackoutCount;      /* Backout counter */
   MQCHAR48  ReplyToQ;          /* Name of reply queue */
   MQCHAR48  ReplyToQMgr;       /* Name of reply queue manager */
   MQCHAR12  UserIdentifier;    /* User identifier */
   MQBYTE32  AccountingToken;   /* Accounting token */
   MQCHAR32  ApplIdentityData;  /* Application data relating to */
                                /* identity */
   MQLONG    PutApplType;       /* Type of application that put the */
                                /* message */
   MQCHAR28  PutApplName;       /* Name of application that put the */
                                /* message */
   MQCHAR8   PutDate;           /* Date when message was put */
   MQCHAR8   PutTime;           /* Time when message was put */
   MQCHAR4   ApplOriginData;    /* Application data relating to */
                                /* origin */
 };
```
https://www.ibm.com/support/knowledgecenter/SSFKSJ_7.5.0/com.ibm.mq.ref.dev.doc/q097730_.htm


```python

class MD(MQOpts):
    """ Construct an MQMD Structure with default values as per MQI.
    The default values may be overridden by the optional keyword arguments 'kw'.
    """
    def __init__(self, **kw):
        super(MD, self).__init__(tuple([
            ['StrucId', CMQC.MQMD_STRUC_ID, '4s'],
            ['Version', CMQC.MQMD_VERSION_1, MQLONG_TYPE],
            ['Report', CMQC.MQRO_NONE, MQLONG_TYPE],
            ['MsgType', CMQC.MQMT_DATAGRAM, MQLONG_TYPE],
            ['Expiry', CMQC.MQEI_UNLIMITED, MQLONG_TYPE],
            ['Feedback', CMQC.MQFB_NONE, MQLONG_TYPE],
            ['Encoding', CMQC.MQENC_NATIVE, MQLONG_TYPE],
            ['CodedCharSetId', CMQC.MQCCSI_Q_MGR, MQLONG_TYPE],
            ['Format', b'', '8s'],
            ['Priority', CMQC.MQPRI_PRIORITY_AS_Q_DEF, MQLONG_TYPE],
            ['Persistence', CMQC.MQPER_PERSISTENCE_AS_Q_DEF, MQLONG_TYPE],
            ['MsgId', b'', '24s'],
            ['CorrelId', b'', '24s'],
            ['BackoutCount', 0, MQLONG_TYPE],
            ['ReplyToQ', b'', '48s'],
            ['ReplyToQMgr', b'', '48s'],
            ['UserIdentifier', b'', '12s'],
            ['AccountingToken', b'', '32s'],
            ['ApplIdentityData', b'', '32s'],
            ['PutApplType', CMQC.MQAT_NO_CONTEXT, MQLONG_TYPE],
            ['PutApplName', b'', '28s'],
            ['PutDate', b'', '8s'],
            ['PutTime', b'', '8s'],
            ['ApplOriginData', b'', '4s'],
            ['GroupId', b'', '24s'],
            ['MsgSeqNumber', 1, MQLONG_TYPE],
            ['Offset', 0, MQLONG_TYPE],
            ['MsgFlags', CMQC.MQMF_NONE, MQLONG_TYPE],
            ['OriginalLength', CMQC.MQOL_UNDEFINED, MQLONG_TYPE]]), **kw)

```

```
docker exec ibm_mq /opt/mqm/samp/bin/amqsevt  -m datadog -q SYSTEM.ADMIN.STATISTICS.QUEUE
```
