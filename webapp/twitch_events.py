# Notifications d'événements Twitch : sub, follow, raid, clip (chat + Discord)
from flask import render_template, request, redirect, url_for

from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import TwitchEventNotification
from discordbot import bot

EVENT_LABELS = {
	"sub": "Abonnement (sub)",
	"follow": "Nouveau follow",
	"raid": "Raid reçu",
	"clip": "Nouveau clip",
}


@webapp.route("/twitch-events")
@require_page("twitch_events")
def open_twitch_events():
	configs = TwitchEventNotification.query.order_by(TwitchEventNotification.event_type).all()
	# S'assurer qu'il existe une config par type
	existing = {c.event_type for c in configs}
	for ev in ("sub", "follow", "raid", "clip"):
		if ev not in existing:
			cfg = TwitchEventNotification(
				event_type=ev,
				message_twitch="Merci {user} !" if ev != "raid" else "Bienvenue aux viewers de {from_broadcaster_name} !",
			)
			db.session.add(cfg)
			configs.append(cfg)
	db.session.commit()
	channels = bot.getAllTextChannel()
	# Nom du canal Discord pour l'affichage
	for c in configs:
		if c.discord_channel_id:
			c.discord_channel_name = next((ch.name for ch in channels if ch.id == c.discord_channel_id), None)
		else:
			c.discord_channel_name = None
	return render_template("twitch-events.html", configs=configs, channels=channels, labels=EVENT_LABELS)


@webapp.route("/twitch-events/save", methods=["POST"])
@require_page("twitch_events")
def save_twitch_events():
	if not can_write_page("twitch_events"):
		return render_template("403.html"), 403
	for ev in ("sub", "follow", "raid", "clip"):
		cfg = TwitchEventNotification.query.filter_by(event_type=ev).first()
		if not cfg:
			cfg = TwitchEventNotification(event_type=ev)
			db.session.add(cfg)
		prefix = f"ev_{ev}_"
		cfg.enable = request.form.get(prefix + "enable") == "1"
		cfg.notify_twitch_chat = request.form.get(prefix + "notify_twitch_chat") == "1"
		cfg.notify_discord = request.form.get(prefix + "notify_discord") == "1"
		ch_id = request.form.get(prefix + "discord_channel_id")
		cfg.discord_channel_id = int(ch_id) if ch_id and ch_id.isdigit() else None
		cfg.message_twitch = (request.form.get(prefix + "message_twitch") or "").strip()[:500]
		cfg.message_discord = (request.form.get(prefix + "message_discord") or "").strip()[:2000] or None
		embed_color = (request.form.get(prefix + "embed_color") or "9146FF").strip().lstrip("#")[:6]
		cfg.embed_color = embed_color if len(embed_color) == 6 else "9146FF"
		cfg.embed_title = (request.form.get(prefix + "embed_title") or "").strip()[:256] or None
		cfg.embed_description = (request.form.get(prefix + "embed_description") or "").strip()[:2000] or None
		cfg.embed_thumbnail = request.form.get(prefix + "embed_thumbnail") == "1"
	db.session.commit()
	return redirect(url_for("open_twitch_events"))


@webapp.route("/twitch-events/toggle/<event_type>")
@require_page("twitch_events")
def toggle_twitch_event(event_type):
	if not can_write_page("twitch_events"):
		return render_template("403.html"), 403
	if event_type not in ("sub", "follow", "raid", "clip"):
		return redirect(url_for("open_twitch_events"))
	cfg = TwitchEventNotification.query.filter_by(event_type=event_type).first()
	if cfg:
		cfg.enable = not cfg.enable
		db.session.commit()
	return redirect(url_for("open_twitch_events"))
