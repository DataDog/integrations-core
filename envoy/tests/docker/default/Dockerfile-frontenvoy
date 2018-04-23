ARG ENVOY_VERSION
FROM envoyproxy/envoy:${ENVOY_VERSION}

CMD /usr/local/bin/envoy -c /etc/front-envoy.yaml --service-cluster front-proxy
