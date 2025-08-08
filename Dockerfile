FROM alpine:3.22.1

WORKDIR /app

RUN apk add --no-cache python3 py3-pip zabbix-agent2

COPY requirements.txt .
COPY bot.py .
COPY statuts.txt .
COPY zabbix_agent2.conf /etc/zabbix/zabbix_agent2.conf
COPY start.sh /start.sh

RUN pip3 install --no-cache-dir --break-system-packages --root-user-action=ignore -r requirements.txt && \
    chmod +x /start.sh

CMD ["/start.sh"]