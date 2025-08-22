from flask import Flask

webapp = Flask(__name__)

from webapp import commandes, configurations, index, humeurs, messages, moderation, protondb
