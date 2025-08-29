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
	for key in request.form : 
		ConfigurationHelper().createOrUpdate(key, request.form.get(key))
	# Je fais ça car HTML n'envoie pas le paramètre de checkbox quand il est décoché
	if (request.form.get("humble_bundle_channel") != None and request.form.get("humble_bundle_enable") == None) :
		ConfigurationHelper().createOrUpdate('humble_bundle_enable', False)
	if (request.form.get("proton_db_api_id") != None and request.form.get("proton_db_enable_enable") == None) :
		ConfigurationHelper().createOrUpdate('proton_db_enable_enable', False)
	db.session.commit()
	return redirect(request.referrer)

@webapp.route("/configurations/twitch/help") 
def twitchConfigurationHelp():
	return render_template("twitch-aide.html")
