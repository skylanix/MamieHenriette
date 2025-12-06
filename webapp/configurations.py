from flask import render_template, request, redirect, url_for, flash
from webapp import webapp
from database import db
from database.helpers import ConfigurationHelper
from discordbot import bot
import asyncio

@webapp.route("/configurations")
def openConfigurations():
	return render_template("configurations.html", configuration = ConfigurationHelper(), channels = bot.getAllTextChannel(), roles = bot.getAllRoles(), guilds = bot.getAllGuilds())

@webapp.route("/configurations/update", methods=['POST']) 
def updateConfiguration():
	checkboxes = {
		'humble_bundle_enable': 'humble_bundle_channel',
		'proton_db_enable_enable': 'proton_db_api_id',
		'moderation_enable': 'moderation_staff_role_ids',
		'moderation_ban_enable': 'moderation_staff_role_ids',
		'moderation_kick_enable': 'moderation_staff_role_ids',
		'welcome_enable': 'welcome_channel_id',
		'leave_enable': 'leave_channel_id',
		'autorole_enable': 'autorole_role_id'
	}
	
	staff_roles = request.form.getlist('moderation_staff_role_ids')
	if staff_roles:
		ConfigurationHelper().createOrUpdate('moderation_staff_role_ids', ','.join(staff_roles))
	else:
		ConfigurationHelper().createOrUpdate('moderation_staff_role_ids', '')
	
	for key in request.form:
		if key == 'moderation_staff_role_ids':
			continue
		value = request.form.get(key)
		if value and value.strip():
			ConfigurationHelper().createOrUpdate(key, value)
	
	for checkbox, reference_field in checkboxes.items():
		if request.form.get(reference_field) is not None and request.form.get(checkbox) is None:
			ConfigurationHelper().createOrUpdate(checkbox, False)
	
	db.session.commit()
	return redirect(request.referrer)

@webapp.route("/configurations/leave-guild", methods=['POST'])
def leaveGuild():
	guild_id = request.form.get('guild_id')
	confirm = request.form.get('confirm_leave')
	
	if not guild_id or not confirm:
		flash('Veuillez sélectionner un serveur et confirmer l\'action.', 'error')
		return redirect(url_for('openConfigurations'))
	
	try:
		guild_id_int = int(guild_id)
		# Exécuter la coroutine dans le loop du bot
		future = asyncio.run_coroutine_threadsafe(bot.leaveGuild(guild_id_int), bot.loop)
		result = future.result(timeout=10)
		
		if result:
			flash('Le bot a quitté le serveur avec succès.', 'success')
		else:
			flash('Serveur non trouvé.', 'error')
	except Exception as e:
		flash(f'Erreur lors de la tentative de quitter le serveur : {str(e)}', 'error')
	
	return redirect(url_for('openConfigurations'))

