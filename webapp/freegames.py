from flask import render_template, request, redirect, url_for, jsonify
from webapp import webapp
from database import db
from database.helpers import ConfigurationHelper
from database.models import FreeGame
from discordbot import bot
from discordbot.freegames import (
	fetchAndStoreGames,
	getPendingGames,
	getAllGames,
	markAsNotified,
	resetNotification,
	KNOWN_SOURCES
)
import asyncio


@webapp.route("/freegames")
def openFreeGames():
	"""Page principale de gestion des jeux gratuits"""
	# Rafraîchir les jeux depuis le flux RSS
	fetchAndStoreGames()
	
	games = getAllGames()
	pending_games = getPendingGames()
	
	return render_template(
		"freegames.html",
		configuration=ConfigurationHelper(),
		channels=bot.getAllTextChannel(),
		roles=bot.getAllRoles(),
		games=games,
		pending_count=len(pending_games),
		sources=KNOWN_SOURCES
	)


@webapp.route("/freegames/config", methods=['POST'])
def updateFreeGamesConfig():
	"""Met à jour la configuration du module Free Games"""
	helper = ConfigurationHelper()
	
	# Gestion de la checkbox enable
	if request.form.get('freegames_channel') is not None:
		if request.form.get('freegames_enable') is None:
			helper.createOrUpdate('freegames_enable', False)
		else:
			helper.createOrUpdate('freegames_enable', 'on')
	
	# Gestion de la checkbox auto_notify
	if request.form.get('freegames_auto_notify') is None:
		helper.createOrUpdate('freegames_auto_notify', False)
	else:
		helper.createOrUpdate('freegames_auto_notify', 'on')
	
	# Canal de notification
	if request.form.get('freegames_channel'):
		helper.createOrUpdate('freegames_channel', request.form.get('freegames_channel'))
	
	# Type de mention
	if request.form.get('freegames_mention_type'):
		helper.createOrUpdate('freegames_mention_type', request.form.get('freegames_mention_type'))
	
	# Rôle à mentionner
	if request.form.get('freegames_mention_role'):
		helper.createOrUpdate('freegames_mention_role', request.form.get('freegames_mention_role'))
	
	# Sources à suivre
	sources = request.form.getlist('freegames_sources')
	helper.createOrUpdate('freegames_sources', ','.join(sources) if sources else '')
	
	db.session.commit()
	return redirect(url_for('openFreeGames'))


@webapp.route("/freegames/notify/<int:game_id>", methods=['POST'])
def notifyFreeGame(game_id):
	"""Envoie une notification pour un jeu spécifique"""
	from discordbot.freegames import notifyGame
	
	try:
		# Utiliser le loop du bot Discord pour exécuter la coroutine
		if bot.loop and bot.loop.is_running():
			future = asyncio.run_coroutine_threadsafe(notifyGame(bot, game_id), bot.loop)
			result = future.result(timeout=30)  # Attendre max 30 secondes
		else:
			return jsonify({'success': False, 'message': 'Le bot Discord n\'est pas connecté'}), 400
		
		if result:
			return jsonify({'success': True, 'message': 'Notification envoyée'})
		else:
			return jsonify({'success': False, 'message': 'Échec de l\'envoi'}), 400
	except Exception as e:
		return jsonify({'success': False, 'message': str(e)}), 500


@webapp.route("/freegames/mark-notified/<int:game_id>", methods=['POST'])
def markGameNotified(game_id):
	"""Marque un jeu comme notifié sans envoyer de message"""
	if markAsNotified(game_id):
		return jsonify({'success': True})
	return jsonify({'success': False}), 400


@webapp.route("/freegames/reset/<int:game_id>", methods=['POST'])
def resetGameNotification(game_id):
	"""Réinitialise le statut de notification d'un jeu"""
	if resetNotification(game_id):
		return jsonify({'success': True})
	return jsonify({'success': False}), 400


@webapp.route("/freegames/refresh", methods=['POST'])
def refreshFreeGames():
	"""Force le rafraîchissement du flux RSS"""
	new_games = fetchAndStoreGames()
	return jsonify({
		'success': True,
		'new_games': len(new_games),
		'message': f'{len(new_games)} nouveau(x) jeu(x) trouvé(s)'
	})


@webapp.route("/freegames/delete/<int:game_id>", methods=['POST'])
def deleteFreeGame(game_id):
	"""Supprime un jeu de la liste"""
	game = FreeGame.query.get(game_id)
	if game:
		db.session.delete(game)
		db.session.commit()
		return jsonify({'success': True})
	return jsonify({'success': False}), 404

