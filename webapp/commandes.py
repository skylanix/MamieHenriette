from flask import render_template, request, redirect, url_for, flash
from webapp import webapp
from database import db
from database.models import Commande

@webapp.route("/commandes")
def commandes():
	commandes_list = Commande.query.all()
	return render_template("commandes.html", commandes=commandes_list)

@webapp.route("/commandes/add", methods=['POST'])
def add_commande():
	trigger = request.form.get('trigger')
	response = request.form.get('response')
	discord_enable = request.form.get('discord_enable') == 'on'
	twitch_enable = request.form.get('twitch_enable') == 'on'
	
	if trigger and response:
		if not trigger.startswith('!'):
			trigger = '!' + trigger
		
		existing = Commande.query.filter_by(trigger=trigger).first()
		if not existing:
			commande = Commande(trigger=trigger, response=response, discord_enable=discord_enable, twitch_enable=twitch_enable)
			db.session.add(commande)
			db.session.commit()
	
	return redirect(url_for('commandes'))

@webapp.route("/commandes/delete/<int:commande_id>")
def delete_commande(commande_id):
	commande = Commande.query.get_or_404(commande_id)
	db.session.delete(commande)
	db.session.commit()
	return redirect(url_for('commandes'))

@webapp.route("/commandes/toggle-discord/<int:commande_id>")
def toggle_discord_commande(commande_id):
	commande = Commande.query.get_or_404(commande_id)
	commande.discord_enable = not commande.discord_enable
	db.session.commit()
	return redirect(url_for('commandes'))

@webapp.route("/commandes/toggle-twitch/<int:commande_id>")
def toggle_twitch_commande(commande_id):
	commande = Commande.query.get_or_404(commande_id)
	commande.twitch_enable = not commande.twitch_enable
	db.session.commit()
	return redirect(url_for('commandes'))
