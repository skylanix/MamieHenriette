import logging

from flask import render_template, request, redirect, url_for
from twitchAPI.twitch import Twitch
from twitchAPI.type import  TwitchAPIException
from twitchAPI.oauth import UserAuthenticator

from database import db
from database.helpers import ConfigurationHelper
from twitchbot import USER_SCOPE
from webapp import webapp


auth: UserAuthenticator

@webapp.route("/configurations/twitch/help") 
def twitchConfigurationHelp():
	return render_template("twitch-aide.html", token_redirect_url = _buildUrl())

@webapp.route("/configurations/twitch/request-token") 
async def twitchRequestToken(): 
	global auth
	helper = ConfigurationHelper()
	twitch = await Twitch(helper.getValue('twitch_client_id'), helper.getValue('twitch_client_secret'))
	auth = UserAuthenticator(twitch, USER_SCOPE, url=_buildUrl())
	return redirect(auth.return_auth_url())

@webapp.route("/configurations/twitch/receive-token") 
async def twitchReceiveToken():
	global auth
	state = request.args.get('state')
	code = request.args.get('code')
	if state != auth.state :
		logging('bad returned state')
		return redirect(url_for('openConfigurations'))
	if code == None :
		logging('no returned state')
		return redirect(url_for('openConfigurations'))
		
	try:
		token, refresh = await auth.authenticate(user_token=code)
		helper = ConfigurationHelper()
		helper.createOrUpdate('twitch_access_token', token)
		helper.createOrUpdate('twitch_refresh_token', refresh)
		db.session.commit()
	except TwitchAPIException as e:
		logging(e)
	return redirect(url_for('openConfigurations'))

# hack pas fou mais on estime qu'on sera toujours en ssl en connecté
def _buildUrl():
	url = f'{request.url_root[:-1]}{url_for('twitchReceiveToken')}'
	if url.find('localhost') != -1 : return url
	url = url.replace('http://', 'https://')
	return url
