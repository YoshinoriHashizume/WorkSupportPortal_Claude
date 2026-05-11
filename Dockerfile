# 開発用（仕様書 `ローカル開発環境構築手順.md` に準拠）
FROM node:22-bookworm-slim
WORKDIR /app

# Oracle Instant Client 64-bit（node-oracledb Thick / ORACLE_CLIENT_LIB_DIR）
# 配布: https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html
ARG ORACLE_IC_ZIP_URL=https://download.oracle.com/otn_software/linux/instantclient/instantclient-basic-linuxx64.zip
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    libaio1 wget unzip ca-certificates \
  && mkdir -p /opt/oracle \
  && wget -q -O /opt/oracle/ic.zip "${ORACLE_IC_ZIP_URL}" \
  && unzip -q -d /opt/oracle /opt/oracle/ic.zip \
  && rm -f /opt/oracle/ic.zip \
  && d="$(ls -d /opt/oracle/instantclient_* | head -n1)" \
  && test -n "$d" && test -d "$d" \
  && ln -sfn "$d" /opt/oracle/instantclient \
  && echo /opt/oracle/instantclient > /etc/ld.so.conf.d/oracle-instantclient.conf \
  && ldconfig \
  && apt-get purge -y wget unzip \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*
ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient

COPY package.json package-lock.json* ./
COPY prisma ./prisma
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
RUN npx prisma generate

EXPOSE 3000
ENV NEXT_TELEMETRY_DISABLED=1
CMD ["npm", "run", "dev"]
