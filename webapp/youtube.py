import re
import requests
from urllib.parse import urlencode
from flask import render_template, request, redirect, url_for
from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import YouTubeNotification
from discordbot import bot


def extract_channel_id(channel_input: str) -> str:
	"""Extrait l'ID de la chaîne YouTube depuis différents formats"""
	if not channel_input:
		return None
	
	channel_input = channel_input.strip()
	
	if channel_input.startswith('UC') and len(channel_input) == 24:
		return channel_input
	
	if '/channel/' in channel_input:
		match = re.search(r'/channel/([a-zA-Z0-9_-]{24})', channel_input)
		if match:
			return match.group(1)
	
	if '/c/' in channel_input or '/user/' in channel_input:
		parts = channel_input.split('/')
		for i, part in enumerate(parts):
			if part in ['c', 'user'] and i + 1 < len(parts):
				handle = parts[i + 1].split('?')[0].split('&')[0]
				channel_id = _get_channel_id_from_handle(handle)
				if channel_id:
					return channel_id
	
	if '@' in channel_input:
		handle = re.search(r'@([a-zA-Z0-9_-]+)', channel_input)
		if handle:
			channel_id = _get_channel_id_from_handle(handle.group(1))
			if channel_id:
				return channel_id
	
	return None


def _get_channel_id_from_handle(handle: str) -> str:
	"""Récupère l'ID de la chaîne depuis un handle en utilisant le flux RSS"""
	try:
		url = f"https://www.youtube.com/@{handle}"
		response = requests.get(url, timeout=10, allow_redirects=True)
		
		if response.status_code == 200:
			channel_id_match = re.search(r'"channelId":"([^"]{24})"', response.text)
			if channel_id_match:
				return channel_id_match.group(1)
			
			canonical_match = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/([^"]{24})"', response.text)
			if canonical_match:
				return canonical_match.group(1)
		
		return None
	except Exception:
		return None


@webapp.route("/youtube")
@require_page("youtube")
def openYouTube():
	notifications: list[YouTubeNotification] = YouTubeNotification.query.all()
	channels = bot.getAllTextChannel()
	for notification in notifications:
		for channel in channels:
			if notification.notify_channel == channel.id:
				notification.notify_channel_name = channel.name
	msg = request.args.get('msg')
	msg_type = request.args.get('type', 'info')
	return render_template("youtube.html", notifications=notifications, channels=channels, msg=msg, msg_type=msg_type)


@webapp.route("/youtube/add", methods=['POST'])
@require_page("youtube")
def addYouTube():
	if not can_write_page("youtube"):
		return render_template("403.html"), 403
	channel_input = request.form.get('channel_id', '').strip()
	channel_id = extract_channel_id(channel_input)
	
	if not channel_id:
		return redirect(url_for("openYouTube") + "?" + urlencode({'msg': f"Impossible d'extraire l'ID de la chaîne depuis : {channel_input}. Veuillez vérifier le lien.", 'type': 'error'}))
	
	notify_channel_str = request.form.get('notify_channel')
	if not notify_channel_str:
		return redirect(url_for("openYouTube") + "?" + urlencode({'msg': "Veuillez sélectionner un canal Discord. Assurez-vous que le bot Discord est connecté.", 'type': 'error'}))
	
	try:
		notify_channel = int(notify_channel_str)
	except ValueError:
		return redirect(url_for("openYouTube") + "?" + urlencode({'msg': "Canal Discord invalide.", 'type': 'error'}))
	
	embed_color = request.form.get('embed_color', 'FF0000').strip().lstrip('#')
	if len(embed_color) != 6:
		embed_color = 'FF0000'
	
	notification = YouTubeNotification(
		enable=True,
		channel_id=channel_id,
		notify_channel=notify_channel,
		message=request.form.get('message'),
		video_type=request.form.get('video_type', 'all'),
		embed_title=request.form.get('embed_title') or None,
		embed_description=request.form.get('embed_description') or None,
		embed_color=embed_color,
		embed_footer=request.form.get('embed_footer') or None,
		embed_author_name=request.form.get('embed_author_name') or None,
		embed_author_icon=request.form.get('embed_author_icon') or None,
		embed_thumbnail=request.form.get('embed_thumbnail') == 'on',
		embed_image=request.form.get('embed_image') == 'on'
	)
	db.session.add(notification)
	db.session.commit()
	return redirect(url_for("openYouTube") + "?" + urlencode({'msg': f"Notification ajoutée avec succès pour la chaîne {channel_id}", 'type': 'success'}))


@webapp.route("/youtube/toggle/<int:id>")
@require_page("youtube")
def toggleYouTube(id):
	if not can_write_page("youtube"):
		return render_template("403.html"), 403
	notification: YouTubeNotification = YouTubeNotification.query.get_or_404(id)
	notification.enable = not notification.enable
	db.session.commit()
	return redirect(url_for("openYouTube"))


@webapp.route("/youtube/edit/<int:id>")
@require_page("youtube")
def openEditYouTube(id):
	notification = YouTubeNotification.query.get_or_404(id)
	channels = bot.getAllTextChannel()
	msg = request.args.get('msg')
	msg_type = request.args.get('type', 'info')
	return render_template("youtube.html", notification=notification, channels=channels, notifications=YouTubeNotification.query.all(), msg=msg, msg_type=msg_type)


@webapp.route("/youtube/edit/<int:id>", methods=['POST'])
@require_page("youtube")
def submitEditYouTube(id):
	if not can_write_page("youtube"):
		return render_template("403.html"), 403
	notification: YouTubeNotification = YouTubeNotification.query.get_or_404(id)
	
	channel_input = request.form.get('channel_id', '').strip()
	channel_id = extract_channel_id(channel_input)
	
	if not channel_id:
		return redirect(url_for("openEditYouTube", id=id) + "?" + urlencode({'msg': f"Impossible d'extraire l'ID de la chaîne depuis : {channel_input}. Veuillez vérifier le lien.", 'type': 'error'}))
	
	notify_channel_str = request.form.get('notify_channel')
	if not notify_channel_str:
		return redirect(url_for("openEditYouTube", id=id) + "?" + urlencode({'msg': "Veuillez sélectionner un canal Discord. Assurez-vous que le bot Discord est connecté.", 'type': 'error'}))
	
	try:
		notify_channel = int(notify_channel_str)
	except ValueError:
		return redirect(url_for("openEditYouTube", id=id) + "?" + urlencode({'msg': "Canal Discord invalide.", 'type': 'error'}))
	
	embed_color = request.form.get('embed_color', 'FF0000').strip().lstrip('#')
	if len(embed_color) != 6:
		embed_color = 'FF0000'
	
	notification.channel_id = channel_id
	notification.notify_channel = notify_channel
	notification.message = request.form.get('message')
	notification.video_type = request.form.get('video_type', 'all')
	notification.embed_title = request.form.get('embed_title') or None
	notification.embed_description = request.form.get('embed_description') or None
	notification.embed_color = embed_color
	notification.embed_footer = request.form.get('embed_footer') or None
	notification.embed_author_name = request.form.get('embed_author_name') or None
	notification.embed_author_icon = request.form.get('embed_author_icon') or None
	notification.embed_thumbnail = request.form.get('embed_thumbnail') == 'on'
	notification.embed_image = request.form.get('embed_image') == 'on'
	db.session.commit()
	return redirect(url_for("openYouTube") + "?" + urlencode({'msg': "Notification modifiée avec succès", 'type': 'success'}))


@webapp.route("/youtube/del/<int:id>")
@require_page("youtube")
def delYouTube(id):
	if not can_write_page("youtube"):
		return render_template("403.html"), 403
	notification = YouTubeNotification.query.get_or_404(id)
	db.session.delete(notification)
	db.session.commit()
	return redirect(url_for("openYouTube"))
