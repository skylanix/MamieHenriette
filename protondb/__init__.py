
import requests
from algoliasearch.search.client import SearchClientSync, SearchConfig, RequestOptions

app_id = "94HE6YATEI"
api_key = "9ba0e69fb2974316cdaec8f5f257088f"

search_name = "call of duty"


config = SearchConfig(app_id, api_key)
config.set_default_hosts()
client = SearchClientSync(app_id, api_key, config=config)
options = RequestOptions(config=config, headers={'referers':'https://www.protondb.com/'})
responses = client.search_single_index(index_name="steamdb",
										search_params={
											"query":"call of duty",
											"facetFilters":[["appType:Game"]],
											"hitsPerPage":50},
										request_options= {'headers':{'Referer':'https://www.protondb.com/'}})
for hit in responses.model_dump().get('hits'): 
	id = hit.get('object_id')
	name:str = hit.get('name')
	if (name.lower().find(search_name.lower())>=0) :
		try:
			response = requests.get(f'http://jazzy-starlight-aeea19.netlify.app/api/v1/reports/summaries/{id}.json')
			if (response.status_code == 200) :
				summmary = response.json()
				tier = summmary.get('tier')
				print(f'{name} : {tier}')
			else :
				print(f'{response.status_code} on {name}({id})')
		except Exception as e:
			print(f'error on {name}({id}): {e}')
	else:
		print(f'{name}({id} ne contient pas {search_name})')
