FROM node:alpine
RUN apk add git python3 --no-cache
RUN pip3 install pyyaml
RUN npm install -g ts-node
WORKDIR /app
RUN npm install typescript @typescript-eslint/parser @typescript-eslint/typescript-estree @types/node
COPY parse_ts.ts /app/parse_ts.ts
COPY validate_log_intgs.py /app/validate_log_intgs.py
