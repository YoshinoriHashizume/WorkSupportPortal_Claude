FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libaio1 libpq-dev unzip wget \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/oracle \
    && wget -q https://download.oracle.com/otn_software/linux/instantclient/2113000/instantclient-basiclite-linux.x64-21.13.0.0.0dbru.zip -O /tmp/instantclient.zip \
    && unzip -q /tmp/instantclient.zip -d /opt/oracle \
    && rm /tmp/instantclient.zip \
    && echo /opt/oracle/instantclient_21_13 > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["sh", "-c", "python manage.py migrate --noinput && if [ \"$AUTH_DEV_MODE\" = \"true\" ]; then python manage.py bootstrap_local_dev; fi && exec python manage.py runserver 0.0.0.0:3000"]
