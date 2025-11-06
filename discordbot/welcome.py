import discord
import logging
from database.helpers import ConfigurationHelper
from discord import Member, TextChannel
from datetime import datetime, timezone

invite_cache = {}

async def updateInviteCache(guild):
	try:
		invites = await guild.invites()
		invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
	except:
		pass

async def getUsedInvite(guild) -> str:
	try:
		new_invites = await guild.invites()
		for invite in new_invites:
			old_uses = invite_cache.get(guild.id, {}).get(invite.code, 0)
			if invite.uses > old_uses:
				await updateInviteCache(guild)
				inviter = f' (créée par {invite.inviter.name})' if invite.inviter else ''
				return f'`{invite.code}`{inviter}'
		await updateInviteCache(guild)
	except:
		pass
	return 'Inconnue'

async def sendWelcomeMessage(bot: discord.Client, member: Member):
	config = ConfigurationHelper()
	
	if not config.getValue('welcome_enable'):
		return
	
	channel_id = config.getIntValue('welcome_channel_id')
	if not channel_id:
		logging.warning('Canal de bienvenue non configuré')
		return
	
	channel = bot.get_channel(channel_id)
	if not channel or not isinstance(channel, TextChannel):
		logging.error(f'Canal de bienvenue {channel_id} introuvable')
		return
	
	welcome_message = config.getValue('welcome_message')
	if not welcome_message:
		welcome_message = 'Bienvenue sur le serveur !'
	
	invite_used = await getUsedInvite(member.guild)
	
	embed = discord.Embed(
		title='🎉 Nouveau membre !',
		description=welcome_message,
		color=discord.Color.green()
	)
	
	embed.set_thumbnail(url=member.display_avatar.url)
	embed.add_field(name='Membre', value=member.mention, inline=True)
	embed.add_field(name='Nombre de membres', value=str(member.guild.member_count), inline=True)
	embed.add_field(name='Invitation utilisée', value=invite_used, inline=False)
	embed.set_footer(text=f'ID: {member.id}')
	
	try:
		await channel.send(embed=embed)
		logging.info(f'Message de bienvenue envoyé pour {member.name}')
	except Exception as e:
		logging.error(f'Échec de l\'envoi du message de bienvenue : {e}')

def formatDuration(seconds: int) -> str:
	days = seconds // 86400
	hours = (seconds % 86400) // 3600
	minutes = (seconds % 3600) // 60
	
	parts = []
	if days > 0:
		parts.append(f'{days} jour{"s" if days > 1 else ""}')
	if hours > 0:
		parts.append(f'{hours} heure{"s" if hours > 1 else ""}')
	if minutes > 0:
		parts.append(f'{minutes} minute{"s" if minutes > 1 else ""}')
	
	if not parts:
		return 'moins d\'une minute'
	
	return ' et '.join(parts)

async def sendLeaveMessage(bot: discord.Client, member: Member):
	config = ConfigurationHelper()
	
	if not config.getValue('leave_enable'):
		return
	
	channel_id = config.getIntValue('leave_channel_id')
	if not channel_id:
		logging.warning('Canal de départ non configuré')
		return
	
	channel = bot.get_channel(channel_id)
	if not channel or not isinstance(channel, TextChannel):
		logging.error(f'Canal de départ {channel_id} introuvable')
		return
	
	leave_message = config.getValue('leave_message')
	if not leave_message:
		leave_message = 'Un membre a quitté le serveur.'
	
	now = datetime.now(timezone.utc)
	duration_seconds = int((now - member.joined_at).total_seconds()) if member.joined_at else 0
	duration_text = formatDuration(duration_seconds)
	
	reason = 'Départ volontaire'
	try:
		async for entry in member.guild.audit_logs(limit=5):
			if not (entry.target and entry.target.id == member.id):
				continue
			
			time_diff = (now - entry.created_at).total_seconds()
			if time_diff > 3:
				continue
			
			if entry.action == discord.AuditLogAction.kick:
				reason = f'Expulsé par {entry.user.mention}'
				if entry.reason:
					reason += f' - Raison: {entry.reason}'
				break
			elif entry.action == discord.AuditLogAction.ban:
				reason = f'Banni par {entry.user.mention}'
				if entry.reason:
					reason += f' - Raison: {entry.reason}'
				break
	except:
		pass
	
	embed = discord.Embed(
		title='👋 Membre parti',
		description=leave_message,
		color=discord.Color.red()
	)
	
	embed.set_thumbnail(url=member.display_avatar.url)
	embed.add_field(name='Membre', value=f'{member.mention} ({member.name})', inline=True)
	embed.add_field(name='Nombre de membres', value=str(member.guild.member_count), inline=True)
	embed.add_field(name='Temps sur le serveur', value=duration_text, inline=False)
	embed.add_field(name='Raison', value=reason, inline=False)
	embed.set_footer(text=f'ID: {member.id}')
	
	try:
		await channel.send(embed=embed)
		logging.info(f'Message de départ envoyé pour {member.name}')
	except Exception as e:
		logging.error(f'Échec de l\'envoi du message de départ : {e}')

