#!/bin/bash

echo "Démarrage du bot Discord..."
LOG_FILE="/app/logs/$(date '+%Y%m%d_%H%M%S').log"
exec /app/venv/bin/python run-web.py 2>&1 | while IFS= read -r line; do
    echo "$(date '+%Y-%m-%d %H:%M:%S%z') $line" | tee -a "$LOG_FILE" # RFC 3339 / ISO 8601
done