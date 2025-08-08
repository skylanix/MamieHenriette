FROM debian:trixie-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    && wget https://repo.zabbix.com/zabbix/7.4/release/debian/pool/main/z/zabbix-release/zabbix-release_latest_7.4+debian12_all.deb \
    && dpkg -i zabbix-release_latest_7.4+debian12_all.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends zabbix-agent2 \
    && rm -rf /var/lib/apt/lists/* \
    && rm zabbix-release_latest_7.4+debian12_all.deb

COPY requirements.txt .
COPY bot.py .
COPY statuts.txt .
COPY zabbix_agent2.conf /etc/zabbix/zabbix_agent2.conf
COPY start.sh /start.sh

RUN pip3 install --no-cache-dir --break-system-packages --root-user-action=ignore -r requirements.txt && \
    chmod +x /start.sh

CMD ["/start.sh"]