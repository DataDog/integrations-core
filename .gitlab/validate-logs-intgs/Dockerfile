FROM node:alpine
RUN apk add git python3 --no-cache
RUN pip3 install pyyaml
RUN npm install -g ts-node
RUN npm install typescript @typescript-eslint/parser @typescript-eslint/typescript-estree @types/node
COPY parse_ts.ts /scripts/parse_ts.ts
COPY validate_log_intgs.py /scripts/validate_log_intgs.py