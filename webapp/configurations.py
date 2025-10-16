from flask import render_template, request, redirect, url_for
from webapp import webapp
from database import db
from database.helpers import ConfigurationHelper
from discordbot import bot

@webapp.route("/configurations")
def openConfigurations():
	return render_template("configurations.html", configuration = ConfigurationHelper(), channels = bot.getAllTextChannel())

@webapp.route("/configurations/update", methods=['POST']) 
def updateConfiguration():
	checkboxes = {
		'humble_bundle_enable': 'humble_bundle_channel',
		'proton_db_enable_enable': 'proton_db_api_id',
		'moderation_enable': 'moderation_staff_role_id',
		'moderation_ban_enable': 'moderation_staff_role_id',
		'moderation_kick_enable': 'moderation_staff_role_id',
		'welcome_enable': 'welcome_channel_id',
		'leave_enable': 'leave_channel_id'
	}
	
	for key in request.form:
		ConfigurationHelper().createOrUpdate(key, request.form.get(key))
	
	for checkbox, reference_field in checkboxes.items():
		if request.form.get(reference_field) is not None and request.form.get(checkbox) is None:
			ConfigurationHelper().createOrUpdate(checkbox, False)
	
	db.session.commit()
	return redirect(request.referrer)

