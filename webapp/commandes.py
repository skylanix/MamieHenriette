from flask import render_template, request, redirect, url_for, flash
from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import Commande

@webapp.route("/commandes")
@require_page("commandes")
def commandes():
	commandes_list = Commande.query.all()
	return render_template("commandes.html", commandes=commandes_list, twitch_permissions=TWITCH_PERMISSIONS)

TWITCH_PERMISSIONS = {'viewer': 'Tous (viewers)', 'sub': 'Abonnés', 'vip': 'VIP', 'moderator': 'Modérateur'}


@webapp.route("/commandes/add", methods=['POST'])
@require_page("commandes")
def add_commande():
	if not can_write_page("commandes"):
		return render_template("403.html"), 403
	trigger = request.form.get('trigger')
	response = request.form.get('response')
	discord_enable = request.form.get('discord_enable') != None
	twitch_enable = request.form.get('twitch_enable') != None
	twitch_permission = request.form.get('twitch_permission') or 'viewer'
	if twitch_permission not in TWITCH_PERMISSIONS:
		twitch_permission = 'viewer'
	
	if trigger and response:
		if not trigger.startswith('!'):
			trigger = '!' + trigger
		
		existing = Commande.query.filter_by(trigger=trigger).first()
		if not existing:
			commande = Commande(trigger=trigger, response=response, discord_enable=discord_enable, twitch_enable=twitch_enable, twitch_permission=twitch_permission)
			db.session.add(commande)
			db.session.commit()
	
	return redirect(url_for('commandes'))

@webapp.route("/commandes/delete/<int:commande_id>")
@require_page("commandes")
def delete_commande(commande_id):
	if not can_write_page("commandes"):
		return render_template("403.html"), 403
	commande = Commande.query.get_or_404(commande_id)
	db.session.delete(commande)
	db.session.commit()
	return redirect(url_for('commandes'))

@webapp.route("/commandes/toggle-discord/<int:commande_id>")
@require_page("commandes")
def toggle_discord_commande(commande_id):
	if not can_write_page("commandes"):
		return render_template("403.html"), 403
	commande = Commande.query.get_or_404(commande_id)
	commande.discord_enable = not commande.discord_enable
	db.session.commit()
	return redirect(url_for('commandes'))

@webapp.route("/commandes/toggle-twitch/<int:commande_id>")
@require_page("commandes")
def toggle_twitch_commande(commande_id):
	if not can_write_page("commandes"):
		return render_template("403.html"), 403
	commande = Commande.query.get_or_404(commande_id)
	commande.twitch_enable = not commande.twitch_enable
	db.session.commit()
	return redirect(url_for('commandes'))
