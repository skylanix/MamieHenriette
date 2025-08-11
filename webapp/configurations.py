from flask import render_template, request, redirect, url_for
from webapp import webapp
from database import db
from database.models import Configuration
from database.helpers import ConfigurationHelper
from discordbot import bot
from discord import TextChannel

@webapp.route("/configurations")
def openConfigurations():
	all = Configuration.query.all()
	channels = []
	for channel in bot.get_all_channels():
		if isinstance(channel, TextChannel):
			channels.append(channel)
	return render_template("configurations.html", configuration = ConfigurationHelper(), channels = channels)

@webapp.route("/configurations/update", methods=['POST']) 
def updateConfiguration():
	for key in request.form : 
		ConfigurationHelper().createOrUpdate(key, request.form.get(key))
	if (request.form.get("humble_bundle_channel") != None and request.form.get("humble_bundle_enable") == None) :
		ConfigurationHelper().createOrUpdate('humble_bundle_enable', False)
	db.session.commit()
	return redirect(url_for('openConfigurations'))
