import asyncio
import logging

from flask import render_template, request, redirect, url_for, flash
from twitchAPI.twitch import Twitch
from twitchAPI.type import TwitchAPIException
from twitchAPI.oauth import UserAuthenticator

from database import db
from database.helpers import ConfigurationHelper
from twitchbot import USER_SCOPE
from webapp import webapp
from webapp.auth import require_page


auth: UserAuthenticator


@webapp.route("/configurations/twitch/help")
@require_page("configurations")
def twitchConfigurationHelp():
	return render_template("twitch-aide.html", token_redirect_url=_buildUrl())


@webapp.route("/configurations/twitch/request-token")
@require_page("configurations")
def twitchRequestToken():
	global auth
	helper = ConfigurationHelper()
	twitch = Twitch(helper.getValue('twitch_client_id'), helper.getValue('twitch_client_secret'))
	auth = UserAuthenticator(twitch, USER_SCOPE, url=_buildUrl())
	return redirect(auth.return_auth_url())


@webapp.route("/configurations/twitch/receive-token")
def twitchReceiveToken():
	global auth
	state = request.args.get('state')
	code = request.args.get('code')

	logging.info("Callback Twitch reçu - state: %s, code: %s", state, code is not None)

	if not hasattr(auth, 'state') or auth is None:
		logging.error('Objet auth non initialisé - veuillez réessayer')
		return redirect(url_for('openConfigurations'))

	if state != auth.state:
		logging.error('State invalide - attendu: %s, reçu: %s', auth.state, state)
		return redirect(url_for('openConfigurations'))
	if code is None:
		logging.error('Pas de code retourné par Twitch')
		return redirect(url_for('openConfigurations'))

	try:
		token, refresh = asyncio.run(auth.authenticate(user_token=code))
		logging.info('Tokens Twitch obtenus avec succès')
		helper = ConfigurationHelper()
		helper.createOrUpdate('twitch_access_token', token)
		helper.createOrUpdate('twitch_refresh_token', refresh)
		db.session.commit()
		logging.info('Tokens Twitch sauvegardés en base de données')
		flash('Token Twitch enregistré. Redémarrez l\'application pour que le bot utilise le nouveau token.', 'success')
	except TwitchAPIException as e:
		logging.error('Erreur API Twitch: %s', e)
		flash(f'Erreur API Twitch : {e}', 'error')
	except Exception as e:
		logging.error('Erreur inattendue: %s', e)
		flash(f'Erreur inattendue : {e}', 'error')
	return redirect(url_for('openConfigurations'))

# hack pas fou mais on estime qu'on sera toujours en ssl en connecté
def _buildUrl():
	url = f'{request.url_root[:-1]}{url_for('twitchReceiveToken')}'
	if url.find('localhost') != -1 : return url
	url = url.replace('http://', 'https://')
	return url
