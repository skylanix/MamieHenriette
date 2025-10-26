import locale
import logging
import threading
import os
from logging.handlers import RotatingFileHandler

from webapp import webapp
from discordbot import bot
from twitchbot import twitchBot


def start_server(): 
    logging.info("Démarrage du serveur web")
    from waitress import serve
    serve(webapp, host="0.0.0.0", port=5000)

def start_discord_bot():
    logging.info("Démarrage du bot Discord")
    with webapp.app_context():
        bot.begin()

def start_twitch_bot():
    logging.info("Démarrage du bot Twitch")
    with webapp.app_context():
        twitchBot.begin()

if __name__ == '__main__':
    # Config logs (console + fichier avec rotation)
    os.makedirs('logs', exist_ok=True)
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s')
    handlers = []
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    handlers.append(stream_handler)
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    handlers.append(file_handler)
    logging.basicConfig(level=logging.INFO, handlers=handlers)

    # Calmer les logs verbeux de certaines libs si besoin
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('discord').setLevel(logging.WARNING)

    # Hook exceptions non-capturées (threads inclus)
    def _log_uncaught(exc_type, exc, tb):
        logging.exception('Exception non capturée', exc_info=(exc_type, exc, tb))
    import sys
    sys.excepthook = _log_uncaught
    if hasattr(threading, 'excepthook'):
        def _thread_excepthook(args):
            logging.exception(f"Exception dans le thread {args.thread.name}", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
        threading.excepthook = _thread_excepthook

    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

    jobs = []
    jobs.append(threading.Thread(target=start_discord_bot, name='discord-bot'))
    jobs.append(threading.Thread(target=start_server, name='web-server'))
    jobs.append(threading.Thread(target=start_twitch_bot, name='twitch-bot'))

    for job in jobs:
        job.start()
    for job in jobs:
        job.join()
