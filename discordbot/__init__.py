import asyncio
import discord
import logging
import random

from database import db
from database.helpers import ConfigurationHelper
from database.models import Configuration, Humeur, Commande
from discord import Message, TextChannel, Member
from discordbot.humblebundle import checkHumbleBundleAndNotify
from discordbot.moderation import (
	handle_warning_command,
	handle_remove_warning_command,
	handle_list_warnings_command,
	handle_ban_command,
	handle_kick_command,
	handle_unban_command,
	handle_inspect_command,
	handle_ban_list_command,
	handle_staff_help_command,
	handle_timeout_command,
	handle_say_command
)
from discordbot.welcome import sendWelcomeMessage, sendLeaveMessage, updateInviteCache
from protondb import searhProtonDb

class DiscordBot(discord.Client):
	async def on_ready(self):
		logging.info(f'Connecté en tant que {self.user} (ID: {self.user.id})')
		for c in self.get_all_channels() :
			logging.info(f'{c.id} {c.name}')
		
		for guild in self.guilds:
			await updateInviteCache(guild)
		
		self.loop.create_task(self.updateStatus())
		self.loop.create_task(self.updateHumbleBundle())
	
	async def updateStatus(self):
		while not self.is_closed():
			humeurs = Humeur.query.all()
			if len(humeurs)>0 :
				humeur = random.choice(humeurs)
				if humeur != None: 
					logging.info(f'Changement de statut : {humeur.text}')
					await self.change_presence(status = discord.Status.online,  activity = discord.CustomActivity(humeur.text))
			await asyncio.sleep(10*60)

	async def updateHumbleBundle(self):
		while not self.is_closed():
			await checkHumbleBundleAndNotify(self)
			await asyncio.sleep(30*60)

	def getAllTextChannel(self) -> list[TextChannel]:
		channels = []
		for channel in self.get_all_channels():
			if isinstance(channel, TextChannel):
				channels.append(channel)
		return channels
	
	def getAllRoles(self):
		guilds_roles = []
		for guild in self.guilds:
			roles = []
			for role in guild.roles:
				if role.name != "@everyone":
					roles.append(role)
			if roles:
				guilds_roles.append({
					'guild_name': guild.name,
					'guild_id': guild.id,
					'roles': roles
				})
		return guilds_roles


	def begin(self) : 
		token = Configuration.query.filter_by(key='discord_token').first()
		if token and token.value and token.value.strip():
			self.run(token.value)
		else :
			logging.error('Aucun token Discord configuré. Le bot ne peut pas être démarré')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
bot = DiscordBot(intents=intents)

# https://discordpy.readthedocs.io/en/stable/quickstart.html
@bot.event
async def on_message(message: Message):
	if message.author == bot.user:
		return
	if not message.content.startswith('!'):
		return
	command_name = message.content.split()[0]
	
	if ConfigurationHelper().getValue('moderation_enable'):
		if command_name in ['!averto', '!av', '!avertissement', '!warn']:
			await handle_warning_command(message, bot)
			return

		if command_name in ['!to', '!timeout']:
			await handle_timeout_command(message, bot)
			return

		if command_name in ['!delaverto', '!removewarn', '!unwarn']:
			await handle_remove_warning_command(message, bot)
			return

		if command_name in ['!listevent', '!listwarn', '!warnings']:
			await handle_list_warnings_command(message, bot)
			return
	
	if ConfigurationHelper().getValue('moderation_ban_enable'):
		if command_name == '!ban':
			await handle_ban_command(message, bot)
			return
		
		if command_name == '!unban':
			await handle_unban_command(message, bot)
			return
		if command_name == '!banlist':
			await handle_ban_list_command(message, bot)
			return
	
	if ConfigurationHelper().getValue('moderation_kick_enable'):
		if command_name == '!kick':
			await handle_kick_command(message, bot)
			return
	
	if ConfigurationHelper().getValue('moderation_enable'):
		if command_name == '!inspect':
			await handle_inspect_command(message, bot)
			return
	
	if command_name == '!say':
		await handle_say_command(message, bot)
		return
	
	if command_name in ['!aide', '!help']:
		await handle_staff_help_command(message, bot)
		return
	
	commande = Commande.query.filter_by(discord_enable=True, trigger=command_name).first()
	if commande:
		try:
			await message.channel.send(commande.response, suppress_embeds=True)
			return
		except Exception as e:
			logging.error(f'Échec de l\'exécution de la commande Discord : {e}')

	if (ConfigurationHelper().getValue('proton_db_enable_enable') and (message.content.startswith('!protondb') or message.content.startswith('!pdb'))):
		if (message.content.find('<@')>0) :
			mention = message.content[message.content.find('<@'):]
		else :
			mention = message.author.mention
		name = message.content
		if name.startswith('!protondb'):
			name = name.replace('!protondb', '', 1)
		elif name.startswith('!pdb'):
			name = name.replace('!pdb', '', 1)
		name = name.replace(f'{mention}', '').strip();
		
		if not name or len(name) == 0:
			try:
				await message.delete()
				delete_time = ConfigurationHelper().getIntValue('proton_db_delete_time') or 10
				help_msg = await message.channel.send(
					f"{mention} ⚠️ Utilisation: `!pdb nom du jeu` ou `!protondb nom du jeu`\n"
					f"Exemple: `!pdb Elden Ring`",
					suppress_embeds=True
				)
				await asyncio.sleep(delete_time)
				await help_msg.delete()
			except Exception as e:
				logging.error(f"Échec de la gestion du message d'aide ProtonDB : {e}")
			return
		
		games = searhProtonDb(name)
		if (len(games)==0) :
			msg = f'{mention} Je n\'ai pas trouvé de jeux correspondant à **{name}**. Es-tu sûr que le jeu est disponible sur Steam ?'
			try:
				await message.channel.send(msg, suppress_embeds=True)
			except Exception as e:
				logging.error(f"Échec de l'envoi du message ProtonDB : {e}")
			return
		total_games = len(games)
		embed = discord.Embed(
			title=f"**{total_games} jeu{'x' if total_games > 1 else ''} trouvé{'s' if total_games > 1 else ''}**",
			color=discord.Color.blurple()
		)
		
		max_fields = 10
		count = 0
		for game in games:
			if count >= max_fields:
				break
			g_name = str(game.get('name'))
			g_id = str(game.get('id'))
			tier = str(game.get('tier') or 'N/A')
			ac_status = game.get('anticheat_status')
			ac_text = ''
			if ac_status:
				status_lower = str(ac_status).lower()
				if status_lower == 'supported':
					ac_emoji, ac_label = '✅', 'Supporté'
				elif status_lower == 'running':
					ac_emoji, ac_label = '⚠️', 'Fonctionne'
				elif status_lower == 'broken':
					ac_emoji, ac_label = '❌', 'Cassé'
				elif status_lower == 'denied':
					ac_emoji, ac_label = '🚫', 'Refusé'
				elif status_lower == 'planned':
					ac_emoji, ac_label = '📅', 'Planifié'
				else:
					ac_emoji, ac_label = '❔', str(ac_status)
				acs = game.get('anticheats') or []
				ac_list = ', '.join([str(ac) for ac in acs if ac])
				ac_text = f" | [Anti-cheat: {ac_emoji} {ac_label}"
				if ac_list:
					ac_text += f" ({ac_list})"
				ac_text += f"](<https://areweanticheatyet.com/game/{g_id}>)"
			
			field_value = f"[{g_name}](<https://www.protondb.com/app/{g_id}>) - **Classé**: {tier}{ac_text}"
			embed.add_field(name="\u200b", value=field_value, inline=False)
			count += 1
		
		rest = max(0, len(games) - count)
		if rest > 0:
			embed.add_field(name="…", value=f"et encore {rest} autres jeux", inline=False)
		
		try : 
			await message.channel.send(content=mention, embed=embed)
		except Exception as e:
			logging.error(f"Échec de l'envoi de l'embed ProtonDB : {e}")

@bot.event
async def on_member_join(member: Member):
	await sendWelcomeMessage(bot, member)

@bot.event
async def on_member_remove(member: Member):
	await sendLeaveMessage(bot, member)

@bot.event
async def on_invite_create(invite):
	await updateInviteCache(invite.guild)

@bot.event
async def on_invite_delete(invite):
	await updateInviteCache(invite.guild)

