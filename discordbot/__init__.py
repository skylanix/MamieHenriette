import asyncio
import discord
import logging
import random

from database import db
from database.helpers import ConfigurationHelper
from database.models import Configuration, Humeur, Commande, DiscordInvite
from datetime import datetime, timezone, timedelta
from discord import Message, TextChannel, Member
from discordbot.humblebundle import checkHumbleBundleAndNotify
from discordbot.freegames import checkFreeGamesAndNotify
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
from discordbot.autorole import assignAutoRole
from protondb import searhProtonDb
from shared_stats import stats_manager, discord_bridge

class DiscordBot(discord.Client):
	async def on_ready(self):
		logging.info(f'Connecté en tant que {self.user} (ID: {self.user.id})')
		for c in self.get_all_channels() :
			logging.info(f'{c.id} {c.name}')
		
		for guild in self.guilds:
			await updateInviteCache(guild)
		
		# Enregistrer le bot dans le bridge pour communication avec Flask
		discord_bridge.register_bot(self, self.loop)
		
		# Mise à jour des stats partagées
		self._update_shared_stats()
		
		# Synchronisation initiale des invitations
		await self.syncInvites()
		
		self.loop.create_task(self.updateStatus())
		self.loop.create_task(self.updateHumbleBundle())
		self.loop.create_task(self.updateFreeGames())
		self.loop.create_task(self._periodic_stats_update())
	
	def _update_shared_stats(self):
		"""Met à jour les statistiques partagées"""
		total_members = sum(g.member_count or 0 for g in self.guilds)
		total_channels = len(list(self.get_all_channels()))
		
		stats_manager.update_discord_stats(
			connected=True,
			guilds=len(self.guilds),
			members=total_members,
			channels=total_channels,
			bot_name=str(self.user),
			bot_id=self.user.id
		)
		
		# Mise à jour des cogs/fonctionnalités activées
		helper = ConfigurationHelper()
		cogs = {
			'Modération': helper.getValue('moderation_enable') or False,
			'Ban': helper.getValue('moderation_ban_enable') or False,
			'Kick': helper.getValue('moderation_kick_enable') or False,
			'ProtonDB': helper.getValue('proton_db_enable_enable') or False,
			'Humeurs': True,  # Toujours actif si le bot tourne
			'Jeux Gratuits': helper.getValue('freegames_enable') or False,
			'Messages de bienvenue': helper.getValue('welcome_enable') or False,
			'Auto-Role': helper.getValue('autorole_enable') or False,
		}
		stats_manager.update_cogs(cogs)
	
	async def _periodic_stats_update(self):
		"""Met à jour les stats périodiquement"""
		while not self.is_closed():
			await asyncio.sleep(60)  # Toutes les minutes
			self._update_shared_stats()
	
	async def updateStatus(self):
		while not self.is_closed():
			humeurs = Humeur.query.all()
			if len(humeurs)>0 :
				humeur = random.choice(humeurs)
				if humeur != None: 
					# Récupérer les stats pour les variables
					total_members = sum(g.member_count or 0 for g in self.guilds)
					total_channels = len(list(self.get_all_channels()))
					
					# Remplacer les variables dans le texte
					status_text = humeur.text
					status_text = status_text.replace('{servers}', str(len(self.guilds)))
					status_text = status_text.replace('{members}', str(total_members))
					status_text = status_text.replace('{channels}', str(total_channels))
					
					logging.info(f'Changement de statut : {status_text}')
					await self.change_presence(status = discord.Status.online,  activity = discord.CustomActivity(status_text))
			await asyncio.sleep(10*60)

	async def updateHumbleBundle(self):
		while not self.is_closed():
			await checkHumbleBundleAndNotify(self)
			await asyncio.sleep(30*60)

	async def updateFreeGames(self):
		while not self.is_closed():
			await checkFreeGamesAndNotify(self)
			await asyncio.sleep(60*60)  # Vérification toutes les heures

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
	
	def getAllGuilds(self):
		"""Retourne la liste de tous les serveurs Discord"""
		guilds_list = []
		for guild in self.guilds:
			guilds_list.append({
				'id': guild.id,
				'name': guild.name,
				'member_count': guild.member_count,
				'icon_url': str(guild.icon.url) if guild.icon else None,
				'owner_id': guild.owner_id
			})
		return guilds_list
	
	async def leaveGuild(self, guild_id: int) -> bool:
		"""Quitte un serveur Discord par son ID"""
		guild = self.get_guild(guild_id)
		if guild:
			await guild.leave()
			logging.info(f'Le bot a quitté le serveur : {guild.name} (ID: {guild_id})')
			return True
		return False

	async def syncInvites(self, guild_id: int = None) -> dict:
		"""Synchronise les invitations Discord avec la base de données"""
		result = {'synced': 0, 'errors': [], 'guilds': []}
		
		guilds_to_sync = [self.get_guild(guild_id)] if guild_id else self.guilds
		
		for guild in guilds_to_sync:
			if not guild:
				continue
			
			try:
				invites = await guild.invites()
				now = datetime.now(timezone.utc)
				
				# Marquer les invitations existantes comme révoquées (on les réactivera si elles existent encore)
				existing_invites = DiscordInvite.query.filter_by(guild_id=str(guild.id), revoked=False).all()
				existing_codes = {inv.code for inv in existing_invites}
				current_codes = {inv.code for inv in invites}
				
				# Marquer comme révoquées celles qui n'existent plus
				for inv in existing_invites:
					if inv.code not in current_codes:
						inv.revoked = True
						inv.last_sync = now
				
				for invite in invites:
					# Calculer la date d'expiration
					expires_at = None
					if invite.max_age and invite.max_age > 0 and invite.created_at:
						expires_at = invite.created_at + timedelta(seconds=invite.max_age)
					
					# Chercher si l'invitation existe déjà
					db_invite = DiscordInvite.query.filter_by(code=invite.code).first()
					
					if db_invite:
						# Mettre à jour l'invitation existante
						db_invite.uses = invite.uses or 0
						db_invite.revoked = False
						db_invite.last_sync = now
						db_invite.channel_name = invite.channel.name if invite.channel else None
						db_invite.inviter_name = invite.inviter.name if invite.inviter else None
					else:
						# Créer une nouvelle invitation
						db_invite = DiscordInvite(
							code=invite.code,
							guild_id=str(guild.id),
							channel_id=str(invite.channel.id) if invite.channel else '',
							channel_name=invite.channel.name if invite.channel else None,
							inviter_id=str(invite.inviter.id) if invite.inviter else None,
							inviter_name=invite.inviter.name if invite.inviter else None,
							uses=invite.uses or 0,
							max_uses=invite.max_uses or 0,
							max_age=invite.max_age or 0,
							temporary=invite.temporary or False,
							created_at=invite.created_at,
							expires_at=expires_at,
							revoked=False,
							last_sync=now
						)
						db.session.add(db_invite)
					
					result['synced'] += 1
				
				db.session.commit()
				result['guilds'].append({'id': guild.id, 'name': guild.name, 'invites': len(invites)})
				logging.info(f'Invitations synchronisées pour {guild.name}: {len(invites)} invitations')
				
			except Exception as e:
				logging.error(f'Erreur lors de la synchronisation des invitations pour {guild.name}: {e}')
				result['errors'].append(f'{guild.name}: {str(e)}')
		
		return result

	async def revokeInvite(self, invite_code: str) -> dict:
		"""Révoque une invitation Discord"""
		result = {'success': False, 'message': '', 'invite_code': invite_code}
		
		try:
			# Chercher l'invitation dans la BDD
			db_invite = DiscordInvite.query.filter_by(code=invite_code).first()
			if not db_invite:
				result['message'] = 'Invitation non trouvée dans la base de données'
				return result
			
			# Récupérer le guild
			guild = self.get_guild(int(db_invite.guild_id))
			if not guild:
				result['message'] = 'Serveur Discord non trouvé'
				return result
			
			# Chercher l'invitation sur Discord
			try:
				invites = await guild.invites()
				discord_invite = next((inv for inv in invites if inv.code == invite_code), None)
				
				if discord_invite:
					await discord_invite.delete(reason='Révoquée via interface web')
					logging.info(f'Invitation {invite_code} révoquée sur Discord')
				
			except Exception as e:
				logging.warning(f'Impossible de révoquer l\'invitation sur Discord: {e}')
			
			# Marquer comme révoquée dans la BDD
			db_invite.revoked = True
			db_invite.last_sync = datetime.now(timezone.utc)
			db.session.commit()
			
			result['success'] = True
			result['message'] = f'Invitation {invite_code} révoquée avec succès'
			
		except Exception as e:
			logging.error(f'Erreur lors de la révocation de l\'invitation {invite_code}: {e}')
			result['message'] = f'Erreur: {str(e)}'
		
		return result

	def getInvites(self, guild_id: int = None, include_revoked: bool = False) -> list:
		"""Récupère les invitations depuis la base de données"""
		query = DiscordInvite.query
		
		if guild_id:
			query = query.filter_by(guild_id=str(guild_id))
		
		if not include_revoked:
			query = query.filter_by(revoked=False)
		
		return query.order_by(DiscordInvite.created_at.desc()).all()

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
		
		try:
			searching_msg = await message.channel.send(f"🔍 Recherche en cours pour **{name}**...")
			games = searhProtonDb(name)
			await searching_msg.delete()
		except:
			games = searhProtonDb(name)
		
		if (len(games)==0) :
			msg = f'{mention} Je n\'ai pas trouvé de jeux correspondant à **{name}**. Es-tu sûr que le jeu est disponible sur Steam ?'
			try:
				await message.channel.send(msg, suppress_embeds=True)
			except Exception as e:
				logging.error(f"Échec de l'envoi du message ProtonDB : {e}")
			return
		total_games = len(games)
		tier_colors = {'platinum': '🟣', 'gold': '🟡', 'silver': '⚪', 'bronze': '🟤', 'borked': '🔴'}
		content = ""
		max_games = 15
		
		for count, game in enumerate(games[:max_games]):
			g_name = str(game.get('name'))
			g_id = str(game.get('id'))
			tier = str(game.get('tier') or 'N/A').lower()
			tier_icon = tier_colors.get(tier, '⚫')
			
			new_entry = f"**[{g_name}](<https://www.protondb.com/app/{g_id}>)**\n{tier_icon} Classé **{tier.capitalize()}**"
			
			ac_status = game.get('anticheat_status')
			if ac_status:
				status_lower = str(ac_status).lower()
				ac_map = {
					'supported': ('✅', 'Supporté'),
					'running': ('⚠️', 'Fonctionne'),
					'broken': ('❌', 'Cassé'),
					'denied': ('🚫', 'Refusé'),
					'planned': ('📅', 'Planifié')
				}
				ac_emoji, ac_label = ac_map.get(status_lower, ('❔', str(ac_status)))
				acs = game.get('anticheats') or []
				ac_list = ', '.join([str(ac) for ac in acs if ac])
				new_entry += f" • [Anti-cheat {ac_emoji} {ac_label}"
				if ac_list:
					new_entry += f" ({ac_list})"
				new_entry += f"](<https://areweanticheatyet.com/game/{g_id}>)"
			
			new_entry += "\n\n"
			
			# Vérifier la limite avant d'ajouter
			if len(content) + len(new_entry) > 3900:
				rest = len(games) - count
				content += f"*... et {rest} autre{'s' if rest > 1 else ''} jeu{'x' if rest > 1 else ''}*"
				break
			
			content += new_entry
		else:
			rest = max(0, len(games) - max_games)
			if rest > 0:
				content += f"*... et {rest} autre{'s' if rest > 1 else ''} jeu{'x' if rest > 1 else ''}*"
		
		embed = discord.Embed(
			title=f"🎮 Résultats ProtonDB - **{total_games} jeu{'x' if total_games > 1 else ''} trouvé{'s' if total_games > 1 else ''}**",
			description=content,
			color=0x5865F2
		)
		
		try : 
			await message.channel.send(embed=embed)
		except Exception as e:
			logging.error(f"Échec de l'envoi de l'embed ProtonDB : {e}")

@bot.event
async def on_member_join(member: Member):
	await sendWelcomeMessage(bot, member)
	await assignAutoRole(bot, member)

@bot.event
async def on_member_remove(member: Member):
	await sendLeaveMessage(bot, member)

@bot.event
async def on_invite_create(invite):
	await updateInviteCache(invite.guild)
	# Synchroniser la nouvelle invitation avec la BDD
	await bot.syncInvites(invite.guild.id)

@bot.event
async def on_invite_delete(invite):
	await updateInviteCache(invite.guild)
	# Marquer l'invitation comme révoquée dans la BDD
	try:
		db_invite = DiscordInvite.query.filter_by(code=invite.code).first()
		if db_invite:
			db_invite.revoked = True
			db_invite.last_sync = datetime.now(timezone.utc)
			db.session.commit()
			logging.info(f'Invitation {invite.code} marquée comme révoquée')
	except Exception as e:
		logging.error(f'Erreur lors de la révocation de l\'invitation {invite.code}: {e}')

