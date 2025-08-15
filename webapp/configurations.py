from flask import render_template, request, redirect, url_for
from webapp import webapp
from database import db
from database.helpers import ConfigurationHelper
from discordbot import bot
from discord import TextChannel

@webapp.route("/configurations")
def openConfigurations():
	channels = []
	for channel in bot.get_all_channels():
		if isinstance(channel, TextChannel):
			channels.append(channel)
	return render_template("configurations.html", configuration = ConfigurationHelper(), channels = channels)

@webapp.route("/configurations/update", methods=['POST']) 
def updateConfiguration():
	for key in request.form : 
		ConfigurationHelper().createOrUpdate(key, request.form.get(key))
	# Je fait ca car html n'envoi pas le parametre de checkbox quand il est décoché
	if (request.form.get("humble_bundle_channel") != None and request.form.get("humble_bundle_enable") == None) :
		ConfigurationHelper().createOrUpdate('humble_bundle_enable', False)
	if (request.form.get("proton_db_api_id") != None and request.form.get("proton_db_enable_enable") == None) :
		ConfigurationHelper().createOrUpdate('proton_db_enable_enable', False)
	db.session.commit()
	return redirect(url_for('openConfigurations'))
