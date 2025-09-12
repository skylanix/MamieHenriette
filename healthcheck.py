#!/usr/bin/env python3

import subprocess
import sys
import os

def check_process():
    """Vérifie si le processus Python principal est en cours d'exécution"""
    try:
        # Vérifier si le processus run-web.py est actif
        result = subprocess.run(
            ["pgrep", "-f", "run-web.py"], 
            capture_output=True, 
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def main():
    if check_process():
        sys.exit(0)  # Succès
    else:
        sys.exit(1)  # Échec

if __name__ == "__main__":
    main()