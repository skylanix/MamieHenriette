from flask import render_template, request, redirect, url_for, flash

from webapp import webapp
from database import db
from database.models import YoutubeAlert
from discordbot import bot
from youtubebot.youtube_alert import _get_channel_name


@webapp.route("/youtube-alert")
def openYoutubeAlert():
	alerts: list[YoutubeAlert] = YoutubeAlert.query.all()
	channels = bot.getAllTextChannel()
	for alert in alerts:
		for channel in channels:
			if alert.notify_channel == channel.id:
				alert.notify_channel_name = channel.name
	return render_template("youtube-alert.html", alerts=alerts, channels=channels)


@webapp.route("/youtube-alert/add", methods=['POST'])
def addYoutubeAlert():
	channel_id = request.form.get('channel_id').strip()
	
	existing = YoutubeAlert.query.filter_by(channel_id=channel_id).first()
	if existing:
		flash("Cette chaîne YouTube est déjà surveillée.", "error")
		return redirect(url_for("openYoutubeAlert"))
	
	channel_name = _get_channel_name(channel_id)
	if not channel_name:
		flash("Impossible de trouver cette chaîne YouTube. Vérifiez l'ID de la chaîne.", "error")
		return redirect(url_for("openYoutubeAlert"))
	
	alert = YoutubeAlert(
		enable=True,
		channel_id=channel_id,
		channel_name=channel_name,
		notify_channel=request.form.get('notify_channel'),
		message=request.form.get('message')
	)
	db.session.add(alert)
	db.session.commit()
	flash(f"Alerte ajoutée pour la chaîne {channel_name}.", "success")
	return redirect(url_for("openYoutubeAlert"))


@webapp.route("/youtube-alert/toggle/<int:id>")
def toggleYoutubeAlert(id):
	alert: YoutubeAlert = YoutubeAlert.query.get_or_404(id)
	alert.enable = not alert.enable
	db.session.commit()
	return redirect(url_for("openYoutubeAlert"))


@webapp.route("/youtube-alert/edit/<int:id>")
def openEditYoutubeAlert(id):
	alert = YoutubeAlert.query.get_or_404(id)
	channels = bot.getAllTextChannel()
	return render_template("youtube-alert.html", alert=alert, channels=channels)


@webapp.route("/youtube-alert/edit/<int:id>", methods=['POST'])
def submitEditYoutubeAlert(id):
	alert: YoutubeAlert = YoutubeAlert.query.get_or_404(id)
	new_channel_id = request.form.get('channel_id').strip()
	
	if new_channel_id != alert.channel_id:
		channel_name = _get_channel_name(new_channel_id)
		if not channel_name:
			flash("Impossible de trouver cette chaîne YouTube. Vérifiez l'ID de la chaîne.", "error")
			return redirect(url_for("openEditYoutubeAlert", id=id))
		alert.channel_id = new_channel_id
		alert.channel_name = channel_name
		alert.last_video_id = None
	
	alert.notify_channel = request.form.get('notify_channel')
	alert.message = request.form.get('message')
	db.session.commit()
	return redirect(url_for("openYoutubeAlert"))


@webapp.route("/youtube-alert/del/<int:id>")
def delYoutubeAlert(id):
	alert = YoutubeAlert.query.get_or_404(id)
	db.session.delete(alert)
	db.session.commit()
	return redirect(url_for("openYoutubeAlert"))
