#!/bin/sh

# Script de démarrage conditionnel pour Zabbix et le bot Discord

# Vérifier si Zabbix est activé
if [ "$ENABLE_ZABBIX" = "true" ]; then
    echo "Zabbix activé - Configuration de l'agent..."
    
    # Remplacer les variables dans la config Zabbix
    sed -i "s/Server=.*/Server=$ZABBIX_SERVER/" /etc/zabbix/zabbix_agent2.conf
    sed -i "s/ServerActive=.*/ServerActive=$ZABBIX_SERVER:10051/" /etc/zabbix/zabbix_agent2.conf
    sed -i "s/Hostname=.*/Hostname=$ZABBIX_HOSTNAME/" /etc/zabbix/zabbix_agent2.conf
    
    zabbix_agent2 -f &
    echo "Zabbix Agent démarré"
else
    echo "Zabbix désactivé"
fi

echo "Démarrage du bot Discord..."
exec python3 bot.py