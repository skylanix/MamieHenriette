import asyncio
import datetime
import discord
import logging
import random
import requests

from database import db
from database.models import Configuration, GameBundle, Humeur

class DiscordBot(discord.Client):
	async def on_ready(self):
		logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
		# for c in self.get_all_channels() :
		# 	print(f'{c.id} {c.name}')
		
		self.loop.create_task(self.updateStatus())
		self.loop.create_task(self.updateHumbleBundle())
	
	async def updateStatus(self):
		humeur = random.choice(Humeur.query.all())
		if humeur != None: 
			logging.info(f'changement de status {humeur.text}')
			await self.change_presence(status = discord.Status.online,  activity = discord.CustomActivity(humeur.text))
		await asyncio.sleep(60)

	async def updateHumbleBundle(self):
		response = requests.get("http://hexas.shionn.org/humble-bundle/json", headers={ "Content-Type": "application/json" })
		if response.status_code == 200:
			bundle = response.json()
			if (GameBundle.query.filter_by(id=bundle['id']).first() == None) :
				choice = bundle['choices'][0]
				date = datetime.datetime.fromtimestamp(bundle['endDate']/1000,datetime.UTC).strftime("%d %B %Y")
				message = f"@here **Humble Bundle** propose un pack de jeu [{bundle['name']}]({bundle['url']}) contenant :\n"
				for game in choice["games"]:
					message += f"- {game}\n"
				message += f"Pour {choice['price']}€, disponible jusqu'au {date}."
				# await self.get_channel(1123512494468644984).send(message)
				# db.session.add(GameBundle(id=bundle['id'], json = bundle))
				# db.session.commit()
		else:
			logging.error(f"Erreur de connexion {response.status_code}")
		await asyncio.sleep(60)
	
	def begin(self) : 
		token = Configuration.query.filter_by(key='discord_token').first()
		if token :
			self.run(token.value)
		else :
			logging.error('pas de token on ne lance pas discord')

intents = discord.Intents.default()
bot = DiscordBot(intents=intents)

