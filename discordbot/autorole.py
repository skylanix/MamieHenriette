import discord
import logging
from database.helpers import ConfigurationHelper
from discord import Member

async def assignAutoRole(bot: discord.Client, member: Member):
	"""Attribue automatiquement un rôle aux nouveaux membres"""
	config = ConfigurationHelper()
	
	if not config.getValue('autorole_enable'):
		return
	
	role_id = config.getIntValue('autorole_role_id')
	if not role_id:
		logging.warning('Auto-role activé mais aucun rôle configuré')
		return
	
	# Chercher le rôle dans le serveur du membre
	role = member.guild.get_role(role_id)
	if not role:
		logging.error(f'Rôle auto-role {role_id} introuvable dans le serveur {member.guild.name}')
		return
	
	try:
		await member.add_roles(role, reason='Auto-role: Attribution automatique à l\'arrivée')
		logging.info(f'Auto-role: Rôle "{role.name}" attribué à {member.name} sur {member.guild.name}')
	except discord.Forbidden:
		logging.error(f'Auto-role: Permission refusée pour attribuer le rôle "{role.name}" à {member.name}')
	except discord.HTTPException as e:
		logging.error(f'Auto-role: Erreur HTTP lors de l\'attribution du rôle : {e}')
	except Exception as e:
		logging.error(f'Auto-role: Erreur inattendue : {e}')

