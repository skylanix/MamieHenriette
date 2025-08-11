
from database import db
from database.models import Configuration

class ConfigurationHelper:
	def getValue(self, key:str) :
		conf = Configuration.query.filter_by(key=key).first()
		if conf == None:
			return None
		if (key.endswith('_enable')) :
			return conf.value in ['true', '1', 'yes', 'on']
		return conf.value
	
	def getIntValue(self, key:str) :
		conf = Configuration.query.filter_by(key=key).first()
		if conf == None:
			return 0
		return int(conf.value)

	def createOrUpdate(self, key:str, value) :
		conf = Configuration.query.filter_by(key=key).first()
		if (key.endswith('_enable')) :
			value = value in ['true', '1', 'yes', 'on']
		if conf :
			conf.value = value
		else :
			conf = Configuration(key = key, value = value)
			db.session.add(conf)




