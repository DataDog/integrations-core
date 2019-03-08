ARG VERSION

FROM lewuathe/presto-base:${VERSION}

COPY etc /usr/local/presto/etc

EXPOSE 8080
EXPOSE 9999

WORKDIR /usr/local/presto
ARG NODE_ID
RUN python scripts/render.py --node-id ${NODE_ID} etc/node.properties.template

ARG NODE_TYPE
COPY ./node_config.sh scripts
RUN chmod +x scripts/node_config.sh
RUN scripts/node_config.sh ${NODE_TYPE}

CMD ["./bin/launcher", "run"]