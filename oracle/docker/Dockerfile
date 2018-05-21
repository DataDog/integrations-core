FROM sath89/oracle-12c

COPY instantclient_12_2-linux2/ /instantclient_12_2-linux2/
COPY instantclient_12_2-darwin/ /instantclient_12_2-darwin/
RUN mkdir -p /instant-client
ENTRYPOINT mkdir -p /instant-client/linux2 && cp -rf /instantclient_12_2-linux2/* /instant-client/linux2 \
    && mkdir -p /instant-client/darwin && cp -rf /instantclient_12_2-darwin/* /instant-client/darwin \
    && /entrypoint.sh
