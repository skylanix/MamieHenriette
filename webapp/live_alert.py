from flask import render_template, request, redirect, url_for

from webapp import webapp
from database import db
from database.models import LiveAlert
from discordbot import bot


@webapp.route("/live-alert")
def openLiveAlert():
	alerts : list[LiveAlert]  = LiveAlert.query.all()
	channels = bot.getAllTextChannel()
	for alert in alerts : 
		for channel in channels:
			if alert.notify_channel == channel.id :
				alert.notify_channel_name = channel.name
	return render_template("live-alert.html", alerts = alerts, channels = channels)

@webapp.route("/live-alert/add",  methods=['POST'])
def addLiveAlert():
	alert = LiveAlert(enable = True, login = request.form.get('login'), notify_channel = request.form.get('notify_channel'), message = request.form.get('message'))
	db.session.add(alert)
	db.session.commit()
	return redirect(url_for("openLiveAlert"))

@webapp.route("/live-alert/toggle/<int:id>")
def toggleLiveAlert(id):
	alert : LiveAlert = LiveAlert.query.get_or_404(id)
	alert.enable = not alert.enable
	db.session.commit()
	return redirect(url_for("openLiveAlert"))

@webapp.route("/live-alert/edit/<int:id>")
def openEditLiveAlert(id):
	alert = LiveAlert.query.get_or_404(id)
	channels = bot.getAllTextChannel()
	return render_template("live-alert.html", alert = alert, channels = channels)

@webapp.route("/live-alert/edit/<int:id>",  methods=['POST'])
def submitEditLiveAlert(id):
	alert : LiveAlert = LiveAlert.query.get_or_404(id)
	alert.login = request.form.get('login')
	alert.notify_channel = request.form.get('notify_channel')
	alert.message = request.form.get('message')
	db.session.commit()
	return redirect(url_for("openLiveAlert"))


@webapp.route("/live-alert/del/<int:id>")
def delLiveAlert(id):
	alert = LiveAlert.query.get_or_404(id)
	db.session.delete(alert)
	db.session.commit()
	return redirect(url_for("openLiveAlert"))
