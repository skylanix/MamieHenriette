
import locale
import logging
import os
import signal
import sys
import threading
from webapp import webapp
from discordbot import bot

def start_server(): 
	logging.info("Start Web Serveur")
	from waitress import serve
	serve(webapp, host="0.0.0.0", port=5000)

def start_discord_bot():
	logging.info("Start Discord Bot")
	with webapp.app_context():
		bot.begin()

def signal_handler(sig, frame):
	logging.info("Arrêt immédiat...")
	os._exit(0)

if __name__ == '__main__':
	locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
	
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	jobs = []
	discord_thread = threading.Thread(target=start_discord_bot)
	server_thread = threading.Thread(target=start_server)
	
	discord_thread.daemon = True
	server_thread.daemon = True
	
	jobs.append(discord_thread)
	jobs.append(server_thread)

	try:
		for job in jobs: job.start()
		for job in jobs: job.join()
	except KeyboardInterrupt:
		logging.info("Arrêt immédiat demandé")
		os._exit(0)


