FROM registry.ddbuild.io/images/mirror/node:12-alpine
RUN apk add git python3 py3-pip --no-cache
RUN python3 -m pip install pyyaml awscli
RUN npm install -g ts-node@9.1.1
WORKDIR /app
RUN npm install typescript@4.2.4 @typescript-eslint/parser@4.23.0 @typescript-eslint/typescript-estree@4.23.0 @types/node@15.3.0
COPY parse_ts.ts /app/parse_ts.ts
COPY validate_log_intgs.py /app/validate_log_intgs.py
