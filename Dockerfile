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
    procps \
    apache2-utils \
    bash 

RUN sed -i 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen; \
    locale-gen; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY run-web.py .
COPY ./database ./database
COPY ./discordbot ./discordbot
COPY ./protondb ./protondb
COPY ./webapp ./webapp
COPY ./twitchbot ./twitchbot
COPY start.sh /start.sh

RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    chmod +x /start.sh && \
    mkdir -p /app/logs

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pgrep python > /dev/null && ! (tail -n 1000 $(ls -t /app/logs/*.log 2>/dev/null | head -1) 2>/dev/null | grep -iE "(ERROR|CRITICAL|Exception|sqlite3\.OperationalError)")

CMD ["/start.sh"]
