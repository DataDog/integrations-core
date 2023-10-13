ARG SOLR_VERSION

FROM solr:${SOLR_VERSION}

# With solr 9, the folder does not exist yet so we create it to avoid permission issues when mounting the logs
# With solr 8, the folder already exists with the right permissions
RUN mkdir -p /var/solr/logs
