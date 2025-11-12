from flask import Flask

webapp = Flask(__name__)

from webapp import commandes, configurations, index, humeurs, protondb, live_alert, twitch_auth, moderation
