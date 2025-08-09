# 
# import discordbot

import multiprocessing
import logging

def start_server(): 
	logging.info("Start Web Serveur")
	from webapp import webapp
	from waitress import serve
	serve(webapp, host="0.0.0.0", port=5000)

def start_discord_bot():
	logging.info("Start Discord Bot")
	from discordbot import bot
	bot.begin()

if __name__ == '__main__':
	jobs = []
	jobs.append(multiprocessing.Process(target=start_server))
	jobs.append(multiprocessing.Process(target=start_discord_bot))

	for job in jobs: job.start()
	for job in jobs: job.join()

