import logging
import requests
import re
import json
from datetime import datetime, timedelta

from algoliasearch.search.client import SearchClientSync, SearchConfig
from database import db
from database.helpers import ConfigurationHelper
from database.models import GameAlias, AntiCheatCache, Configuration
from sqlalchemy import desc, func

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

def _should_update_anticheat_cache() -> bool:
	try:
		last_update_conf = Configuration.query.filter_by(key='anticheat_last_update').first()
		if not last_update_conf:
			return True
		try:
			last_update = datetime.fromisoformat(last_update_conf.value)
			return datetime.now() - last_update > timedelta(days=7)
		except:
			return True
	except Exception as e:
		logging.error(f'Erreur lors de la vérification du cache anti-cheat: {e}')
		return False

def _fetch_anticheat_data():
	try:
		url = 'https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/master/games.json'
		response = requests.get(url, timeout=10)
		if response.status_code == 200:
			return response.json()
		else:
			logging.error(f'Échec de la récupération des données anti-cheat. Code HTTP: {response.status_code}')
			return None
	except Exception as e:
		logging.error(f'Erreur lors de la récupération des données anti-cheat: {e}')
		return None

def _update_anticheat_cache_if_needed():
	try:
		if not _should_update_anticheat_cache():
			return
		
		logging.info('Mise à jour du cache anti-cheat...')
		anticheat_data = _fetch_anticheat_data()
		if not anticheat_data:
			return
		
		for game in anticheat_data:
			try:
				steam_id = str(game.get('storeIds', {}).get('steam', ''))
				if not steam_id or steam_id == '0':
					continue
				
				cache_entry = AntiCheatCache.query.filter_by(steam_id=steam_id).first()
				
				status = game.get('status', 'Unknown')
				anticheats_list = game.get('anticheats', [])
				anticheats_str = json.dumps(anticheats_list) if anticheats_list else None
				reference = game.get('reference', '')
				notes_data = game.get('notes', '')
				if isinstance(notes_data, list):
					notes = json.dumps(notes_data)
				else:
					notes = str(notes_data) if notes_data else ''
				game_name = game.get('name', '')
				
				if cache_entry:
					cache_entry.game_name = game_name
					cache_entry.status = status
					cache_entry.anticheats = anticheats_str
					cache_entry.reference = reference
					cache_entry.notes = notes
					cache_entry.updated_at = datetime.now()
				else:
					cache_entry = AntiCheatCache(
						steam_id=steam_id,
						game_name=game_name,
						status=status,
						anticheats=anticheats_str,
						reference=reference,
						notes=notes,
						updated_at=datetime.now()
					)
					db.session.add(cache_entry)
			except Exception as e:
				logging.error(f'Erreur lors de la mise à jour du jeu {game.get("name")}: {e}')
				continue
		
		last_update_conf = Configuration.query.filter_by(key='anticheat_last_update').first()
		if last_update_conf:
			last_update_conf.value = datetime.now().isoformat()
		else:
			last_update_conf = Configuration(key='anticheat_last_update', value=datetime.now().isoformat())
			db.session.add(last_update_conf)
		
		db.session.commit()
		logging.info('Cache anti-cheat mis à jour avec succès')
	except Exception as e:
		try:
			db.session.rollback()
		except:
			pass
		logging.error(f'Erreur lors de la mise à jour du cache anti-cheat: {e}')

def _get_anticheat_info(steam_id: str) -> dict:
	try:
		cache_entry = AntiCheatCache.query.filter_by(steam_id=steam_id).first()
		if not cache_entry:
			return None
		
		try:
			anticheats = json.loads(cache_entry.anticheats) if cache_entry.anticheats else []
		except:
			anticheats = []
		
		return {
			'status': cache_entry.status,
			'anticheats': anticheats,
			'reference': cache_entry.reference,
			'notes': cache_entry.notes
		}
	except Exception as e:
		logging.error(f'Erreur lors de la récupération des infos anti-cheat pour {steam_id}: {e}')
		return None

def searhProtonDb(search_name:str): 
	results = []
	search_name = _apply_game_aliases(search_name)
	
	try:
		_update_anticheat_cache_if_needed()
	except Exception as e:
		logging.error(f'Erreur lors de la mise à jour du cache anti-cheat: {e}')
	
	responses = _call_algoliasearch(search_name)
	for hit in responses.model_dump().get('hits'): 
		id = hit.get('object_id')
		name:str = hit.get('name')
		if (_is_name_match(name, search_name)) :
			try:
				summmary = _call_summary(id)
				if (summmary != None) :
					tier = summmary.get('tier')
					
					anticheat_info = None
					try:
						anticheat_info = _get_anticheat_info(str(id))
					except Exception as e:
						logging.error(f'Erreur lors de la récupération anti-cheat pour {name}: {e}')
					
					result = {
						'id':id, 
						'name' : name,
						'tier' : tier
					}
					
					if anticheat_info:
						result['anticheat_status'] = anticheat_info.get('status')
						result['anticheats'] = anticheat_info.get('anticheats', [])
						result['anticheat_reference'] = anticheat_info.get('reference')
						result['anticheat_notes'] = anticheat_info.get('notes')
					
					results.append(result)
					logging.info(f'Trouvé {name}({id}) : {tier}' + (f' [Anti-cheat: {anticheat_info.get("status")}]' if anticheat_info else ''))
			except Exception as e:
				logging.error(f'Erreur lors du traitement du jeu {name} (ID: {id}) : {e}')
		else:
			logging.info(f'{name}({id}) ne contient pas {search_name}')
	return results

