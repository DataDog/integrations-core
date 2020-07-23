# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import click

from ..console import CONTEXT_SETTINGS


@click.group(context_settings=CONTEXT_SETTINGS, short_help='JMX utilities')
def jmx():
    pass


@jmx.command(context_settings=CONTEXT_SETTINGS, short_help='Query endpoint for JMX info')
@click.argument('host')
@click.argument('port')
@click.argument('domain', default="*")
@click.pass_context
def query_endpoint(ctx, host, port, domain):
    import jpype
    from jpype import java
    from jpype import javax

    url = "service:jmx:rmi:///jndi/rmi://{}:{}/jmxrmi".format(host, port)
    jpype.startJVM(convertStrings=False)

    jhash = java.util.HashMap()
    jmxurl = javax.management.remote.JMXServiceURL(url)
    jmxsoc = javax.management.remote.JMXConnectorFactory.connect(jmxurl, jhash)
    connection = jmxsoc.getMBeanServerConnection()

    query = javax.management.ObjectName("{}:*".format(domain))
    beans = connection.queryMBeans(query, None)
    for bean in list(beans):
        bean_name = bean.getObjectName().toString()
        print("Bean: {}".format(bean_name))
        info = connection.getMBeanInfo(javax.management.ObjectName(bean_name))
        attrs = info.getAttributes()
        for attr in list(attrs):
            print("    {:20}: {}".format(str(attr.getName()), attr.getDescription()))
