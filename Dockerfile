FROM debian:trixie-slim

# Métadonnées de l'image
LABEL org.opencontainers.image.title="MamieHenriette"
LABEL org.opencontainers.image.description="Bot multi-plateformes Discord/Twitch/YouTube pour la communauté STEvE"
LABEL org.opencontainers.image.authors="skylanix"
LABEL org.opencontainers.image.source="https://github.com/skylanix/MamieHenriette"
LABEL org.opencontainers.image.url="https://github.com/skylanix/MamieHenriette"

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
    wget \
    && wget https://repo.zabbix.com/zabbix/7.4/release/debian/pool/main/z/zabbix-release/zabbix-release_latest_7.4+debian12_all.deb \
    && dpkg -i zabbix-release_latest_7.4+debian12_all.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends zabbix-agent2 \
    && sed -i 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/* \
    && rm zabbix-release_latest_7.4+debian12_all.deb

COPY requirements.txt .
COPY run-web.py .
COPY ./webapp ./webapp
COPY ./discordbot ./discordbot
COPY ./database ./database
COPY zabbix_agent2.conf /etc/zabbix/zabbix_agent2.conf
COPY start.sh /start.sh

RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    chmod +x /start.sh

CMD ["/start.sh"]