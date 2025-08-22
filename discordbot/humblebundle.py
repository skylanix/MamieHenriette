import datetime
import logging
import json
import requests

from database import db
from database.helpers import ConfigurationHelper
from database.models import  GameBundle
from discord import Client


def _isEnable():
	return ConfigurationHelper().getValue('humble_bundle_enable') and ConfigurationHelper().getIntValue('humble_bundle_channel') != 0

def _callHexas():
	response = requests.get("http://hexas.shionn.org/humble-bundle/json", headers={ "Content-Type": "application/json" })
	if response.status_code == 200:
		return response.json()
	logging.error(f"Échec de la connexion à l'API Humble Bundle. Code de statut HTTP : {response.status_code}")
	return None

def _isNotAlreadyNotified(bundle):
	return GameBundle.query.filter_by(id=bundle['id']).first() == None

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
			bundle = _callHexas()
			if bundle != None and _isNotAlreadyNotified(bundle) :
				message = _formatMessage(bundle)
				await bot.get_channel(ConfigurationHelper().getIntValue('humble_bundle_channel')).send(message)
				db.session.add(GameBundle(id=bundle['id'], name=bundle['name'], json = json.dumps(bundle)))
				db.session.commit()
		except Exception as e:
			logging.error(f"Échec de la vérification des offres Humble Bundle : {e}")
	else: 
		logging.info('Humble Bundle est désactivé')

