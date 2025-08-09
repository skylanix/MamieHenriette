from flask import render_template, request, redirect, url_for
from webapp import webapp
from database import db
from database.models import Configuration

@webapp.route("/configurations")
def openConfigurations():
	return render_template("configurations.html")

@webapp.route('/configurations/set/<key>', methods=['POST'])
def setConfiguration(key):
	conf = Configuration.query.filter_by(key=key).first()
	if conf :
		conf.value = request.form['value']
	else :
		conf = Configuration(key = key, value = request.form['value'])
		db.session.add(conf)
	db.session.commit()
	return redirect(url_for('openConfigurations'))
