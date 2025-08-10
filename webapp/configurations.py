from flask import render_template, request, redirect, url_for
from webapp import webapp
from database import db
from database.models import Configuration
from discordbot import bot

@webapp.route("/configurations")
def openConfigurations():
	all = Configuration.query.all()
	configurations = {conf.key: conf for conf in all}
	return render_template("configurations.html", configurations = configurations, channels = bot.get_all_channels())

@webapp.route("/updateConfiguration", methods=['POST']) 
def updateConfiguration():
	
	return redirect(url_for('openConfigurations'))


@webapp.route('/configurations/set/<key>', methods=['POST'])
def setConfiguration(key):
	conf = Configuration.query.filter_by(key=key).first()
	if conf :
		conf.value = request.form['value']
	else :
		conf = Configuration(key = key, value = request.form['value'])
		db.session.add(conf)
	db.session.commit()
	return redirect(url_for('openConfigurations'))
