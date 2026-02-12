from flask import render_template, request, redirect, url_for

from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import LiveAlert
from discordbot import bot


@webapp.route("/live-alert")
@require_page("live_alert")
def openLiveAlert():
	alerts : list[LiveAlert]  = LiveAlert.query.all()
	channels = bot.getAllTextChannel()
	for alert in alerts : 
		for channel in channels:
			if alert.notify_channel == channel.id :
				alert.notify_channel_name = channel.name
	return render_template("live-alert.html", alerts = alerts, channels = channels)

@webapp.route("/live-alert/add",  methods=['POST'])
@require_page("live_alert")
def addLiveAlert():
	if not can_write_page("live_alert"):
		return render_template("403.html"), 403
	embed_color = (request.form.get('embed_color') or '9146FF').strip().lstrip('#')
	if len(embed_color) != 6:
		embed_color = '9146FF'
	alert = LiveAlert(
		enable=True,
		login=request.form.get('login'),
		notify_channel=request.form.get('notify_channel'),
		message=(request.form.get('message') or '').strip(),
		watch_activity=request.form.get('watch_activity') == '1',
		embed_title=request.form.get('embed_title') or None,
		embed_description=request.form.get('embed_description') or None,
		embed_color=embed_color,
		embed_footer=request.form.get('embed_footer') or None,
		embed_author_name=request.form.get('embed_author_name') or None,
		embed_author_icon=request.form.get('embed_author_icon') or None,
		embed_thumbnail=request.form.get('embed_thumbnail') == 'on',
		embed_image=request.form.get('embed_image') == 'on',
	)
	db.session.add(alert)
	db.session.commit()
	return redirect(url_for("openLiveAlert"))

@webapp.route("/live-alert/toggle/<int:id>")
@require_page("live_alert")
def toggleLiveAlert(id):
	if not can_write_page("live_alert"):
		return render_template("403.html"), 403
	alert : LiveAlert = LiveAlert.query.get_or_404(id)
	alert.enable = not alert.enable
	db.session.commit()
	return redirect(url_for("openLiveAlert"))

@webapp.route("/live-alert/edit/<int:id>")
@require_page("live_alert")
def openEditLiveAlert(id):
	alert = LiveAlert.query.get_or_404(id)
	channels = bot.getAllTextChannel()
	return render_template("live-alert.html", alert = alert, channels = channels)

@webapp.route("/live-alert/edit/<int:id>",  methods=['POST'])
@require_page("live_alert")
def submitEditLiveAlert(id):
	if not can_write_page("live_alert"):
		return render_template("403.html"), 403
	alert: LiveAlert = LiveAlert.query.get_or_404(id)
	embed_color = (request.form.get('embed_color') or '9146FF').strip().lstrip('#')
	if len(embed_color) != 6:
		embed_color = '9146FF'
	alert.login = request.form.get('login')
	alert.notify_channel = request.form.get('notify_channel')
	alert.message = (request.form.get('message') or '').strip()
	alert.watch_activity = request.form.get('watch_activity') == '1'
	alert.embed_title = request.form.get('embed_title') or None
	alert.embed_description = request.form.get('embed_description') or None
	alert.embed_color = embed_color
	alert.embed_footer = request.form.get('embed_footer') or None
	alert.embed_author_name = request.form.get('embed_author_name') or None
	alert.embed_author_icon = request.form.get('embed_author_icon') or None
	alert.embed_thumbnail = request.form.get('embed_thumbnail') == 'on'
	alert.embed_image = request.form.get('embed_image') == 'on'
	db.session.commit()
	return redirect(url_for("openLiveAlert"))

@webapp.route("/live-alert/toggle-watch/<int:id>")
@require_page("live_alert")
def toggleWatchActivity(id):
	if not can_write_page("live_alert"):
		return render_template("403.html"), 403
	alert : LiveAlert = LiveAlert.query.get_or_404(id)
	alert.watch_activity = not alert.watch_activity
	db.session.commit()
	return redirect(url_for("openLiveAlert"))


@webapp.route("/live-alert/del/<int:id>")
@require_page("live_alert")
def delLiveAlert(id):
	if not can_write_page("live_alert"):
		return render_template("403.html"), 403
	alert = LiveAlert.query.get_or_404(id)
	db.session.delete(alert)
	db.session.commit()
	return redirect(url_for("openLiveAlert"))
