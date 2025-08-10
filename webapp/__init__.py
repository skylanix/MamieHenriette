from flask import Flask
from discordbot import bot

webapp = Flask(__name__)

from webapp import commandes, configurations, index, humeurs, messages, moderation
