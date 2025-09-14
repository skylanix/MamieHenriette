#!/bin/bash

echo "Démarrage du bot Discord..."
exec /app/venv/bin/python run-web.py 2>&1 | tee >(rotatelogs /app/logs/app.log.%Y%m%d-%H%M%S 50M)