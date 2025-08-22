
import logging
import requests
import re

from algoliasearch.search.client import SearchClientSync, SearchConfig
from database.helpers import ConfigurationHelper
from database.models import GameAlias
from sqlalchemy import desc,func

def _call_algoliasearch(search_name:str): 
	config = SearchConfig(ConfigurationHelper().getValue('proton_db_api_id'), 
						ConfigurationHelper().getValue('proton_db_api_key'))
	config.set_default_hosts()
	client = SearchClientSync(config=config)
	return client.search_single_index(index_name="steamdb",
											search_params={
												"query":search_name,
												"facetFilters":[["appType:Game"]],
												"hitsPerPage":50},
											request_options= {'headers':{'Referer':'https://www.protondb.com/'}})

def _call_summary(id): 
	response = requests.get(f'http://jazzy-starlight-aeea19.netlify.app/api/v1/reports/summaries/{id}.json')
	if (response.status_code == 200) :
		return response.json()
	logging.error(f'Échec de la récupération des données ProtonDB pour le jeu {id}. Code de statut HTTP : {response.status_code}')
	return None

def _is_name_match(name:str, search_name:str) -> bool:
	normalized_game_name = re.sub("[^a-z0-9]", "", name.lower())
	normalized_search_name = re.sub("[^a-z0-9]", "", search_name.lower())
	return normalized_game_name.find(normalized_search_name) >= 0

def _apply_game_aliases(search_name:str) -> str:
	for alias in GameAlias.query.order_by(desc(func.length(GameAlias.alias))).all():
		search_name = re.sub(re.escape(alias.alias), alias.name, search_name, flags=re.IGNORECASE)
	return search_name

def searhProtonDb(search_name:str): 
	results = []
	search_name = _apply_game_aliases(search_name)
	responses = _call_algoliasearch(search_name)
	for hit in responses.model_dump().get('hits'): 
		id = hit.get('object_id')
		name:str = hit.get('name')
		if (_is_name_match(name, search_name)) :
			try:
				summmary = _call_summary(id)
				if (summmary != None) :
					tier = summmary.get('tier')
					results.append({
						'id':id, 
						'name' : name,
						'tier' : tier
					})
					logging.info(f'Trouvé {name}({id}) : {tier}')
			except Exception as e:
				logging.error(f'Erreur lors du traitement du jeu {name} (ID: {id}) : {e}')
		else:
			logging.info(f'{name}({id}) ne contient pas {search_name}')
	return results

