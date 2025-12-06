from flask import Flask
import os

webapp = Flask(__name__)
webapp.secret_key = os.environ.get('FLASK_SECRET_KEY', 'mamie-henriette-secret-key-change-me')

from webapp import commandes, configurations, index, humeurs, protondb, live_alert, twitch_auth, moderation, freegames, youtube_alert
