import asyncio
import datetime
import logging
import json
import requests

from database import db
from database.helpers import ConfigurationHelper
from database.models import  GameBundle
from discord import Client


def _isEnable():
	helper = ConfigurationHelper()
	return helper.getValue('humble_bundle_enable') and helper.getIntValue('humble_bundle_channel') != 0 

def _callGithub(): 
	try:
		response = requests.get("https://raw.githubusercontent.com/shionn/HumbleBundleGamePack/refs/heads/master/data/game-bundles.json", timeout=30)
		if response.status_code == 200:
			return response.json()
		logging.error(f"Échec de la connexion à la ressource Humble Bundle. Code de statut HTTP : {response.status_code}")
		return None
	except (requests.exceptions.SSLError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
		logging.error(f"Erreur de connexion à la ressource Humble Bundle : {e}")
		return None
	except Exception as e:
		logging.error(f"Erreur inattendue lors de la récupération des bundles : {e}")
		return None

def _isNotAlreadyNotified(bundle):
	return GameBundle.query.filter_by(url=bundle['url']).first() == None

def _findFirstNotNotified(bundles) :
	if bundles != None :
		for bundle in bundles: 
			if _isNotAlreadyNotified(bundle) :
				return bundle
	return None

def _formatMessage(bundle):
	choice = bundle['choices'][0]
	date = datetime.datetime.fromtimestamp(bundle['endDate']/1000,datetime.UTC).strftime("%d %B %Y")
	message = f"@here **Humble Bundle** propose un pack de jeu [{bundle['name']}]({bundle['url']}) contenant :\n"
	for game in choice["games"]:
		message += f"- {game}\n"
	message += f"Pour {choice['price']}€, disponible jusqu'au {date}."
	return message

async def checkHumbleBundleAndNotify(bot: Client):
	if _isEnable() :
		try : 
			bundles = _callGithub()
			bundle = _findFirstNotNotified(bundles)
			if bundle != None :
				message = _formatMessage(bundle)
				try:
					await asyncio.wait_for(bot.get_channel(ConfigurationHelper().getIntValue('humble_bundle_channel')).send(message), timeout=30.0)
					db.session.add(GameBundle(url=bundle['url'], name=bundle['name'], json = json.dumps(bundle)))
					db.session.commit()
				except asyncio.TimeoutError:
					logging.error(f'Timeout lors de l\'envoi du message Humble Bundle')
				except Exception as send_error:
					logging.error(f'Erreur lors de l\'envoi du message Humble Bundle : {send_error}')
		except Exception as e:
			logging.error(f"Échec de la vérification des offres Humble Bundle : {e}")
	else: 
		logging.info('Humble Bundle est désactivé')

