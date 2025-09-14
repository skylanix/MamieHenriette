FROM debian:trixie-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=fr_FR.UTF-8
ENV LC_ALL=fr_FR.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    locales \
    python3 \
    python3-pip \
    python3-venv \
    procps 

RUN wget https://repo.zabbix.com/zabbix/7.4/release/debian/pool/main/z/zabbix-release/zabbix-release_latest_7.4+debian13_all.deb; \
    dpkg -i zabbix-release*; \
    apt-get update; \
    apt-get install -y --no-install-recommends zabbix-agent2; \
    sed -i 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen; \
    locale-gen; \
    rm -rf /var/lib/apt/lists/* *.deb

COPY requirements.txt .
COPY run-web.py .
COPY ./database ./database
COPY ./discordbot ./discordbot
COPY ./protondb ./protondb
COPY ./webapp ./webapp
COPY ./twitchbot ./twitchbot
COPY zabbix_agent2.conf /etc/zabbix/zabbix_agent2.conf
COPY start.sh /start.sh

RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    chmod +x /start.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pgrep python > /dev/null || exit 1

CMD ["/start.sh"]
