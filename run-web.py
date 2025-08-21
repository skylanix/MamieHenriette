import locale
import logging
import threading

from discordbot import bot
from webapp import webapp
# from twitchbot import twitchBot


def start_server(): 
    logging.info("Start Web Serveur")
    from waitress import serve
    serve(webapp, host="0.0.0.0", port=5000)

def start_discord_bot():
    logging.info("Start Discord Bot")
    with webapp.app_context():
        bot.begin()

# def start_twitch_bot():
#     logging.info("Start Twitch Bot")
#     with webapp.app_context():
#         twitchBot.begin()

if __name__ == '__main__':
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

    jobs = []
    jobs.append(threading.Thread(target=start_discord_bot))
    jobs.append(threading.Thread(target=start_server))
    # jobs.append(threading.Thread(target=start_twitch_bot))

    for job in jobs: job.start()
    for job in jobs: job.join()
