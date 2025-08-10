
import locale
import logging
import multiprocessing
from webapp import webapp
from discordbot import bot

def start_server(): 
	logging.info("Start Web Serveur")
	from waitress import serve
	serve(webapp, host="0.0.0.0", port=5000)
	# webapp.run()

def start_discord_bot():
	logging.info("Start Discord Bot")
	with webapp.app_context():
		bot.begin()

if __name__ == '__main__':
	locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

	jobs = []
	jobs.append(multiprocessing.Process(target=start_discord_bot))
	jobs.append(multiprocessing.Process(target=start_server))

	for job in jobs: job.start()

	print(bot.get_all_channels())

	for job in jobs: job.join()


