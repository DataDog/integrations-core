ARG CASSANDRA_VERSION
FROM cassandra:${CASSANDRA_VERSION}
COPY jmxremote.password /etc/cassandra/jmxremote.password
RUN chown cassandra:cassandra /etc/cassandra/jmxremote.password
RUN chmod 400 /etc/cassandra/jmxremote.password
CMD ["cassandra", "-f"]
