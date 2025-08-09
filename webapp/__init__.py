from flask import Flask

webapp = Flask(__name__)

from webapp import commandes, index, humeurs, messages, moderation
