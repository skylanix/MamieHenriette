import random
import discord
# import os
import logging
import asyncio
from webapp import webapp
from database.models import Configuration, Humeur

class DiscordBot(discord.Client):
	async def on_ready(self):
		logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
		for c in self.get_all_channels() :
			logging.info(f'{c.id} {c.name}')
		self.loop.create_task(self.updateStatus())
		# await self.get_channel(1123512494468644984).send("essai en python")
	
	async def updateStatus(self):
		# from database.models import Humeur
		humeur = random.choice(Humeur.query.all())
		if humeur != None: 
			logging.info(f'changement de status {humeur.text}')
			await self.change_presence(status = discord.Status.online,  activity = discord.CustomActivity(humeur.text))
		await asyncio.sleep(60)

	def begin(self) : 
		with webapp.app_context():
			token = Configuration.query.filter_by(key='discord_token').first()
			if token :
				self.run(token.value)
			else :
				logging.error('pas de token on ne lance pas discord')

intents = discord.Intents.default()
bot = DiscordBot(intents=intents)
