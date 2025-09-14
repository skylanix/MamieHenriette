#!/bin/bash

echo "Démarrage du bot Discord..."
exec /app/venv/bin/python run-web.py 2>&1 | while IFS= read -r line; do
    echo "$(date '+%Y-%m-%d %H:%M:%S%z') $line" | tee -a /app/logs/$(hostname).log # RFC 3339 / ISO 8601
done