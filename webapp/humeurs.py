from flask import render_template, request, redirect, url_for
from webapp import webapp
from database import db
from database.models import Humeur

@webapp.route("/humeurs")
def listHumeurs():
	humeurs = Humeur.query.all()
	return render_template("humeurs.html", humeurs = humeurs)

@webapp.route('/humeurs/add', methods=['POST'])
def addHumeur():
	humeur = Humeur(text=request.form['text'])
	db.session.add(humeur)
	db.session.commit()
	return redirect(url_for('listHumeurs'))

@webapp.route('/humeurs/del/<id>')
def delHumeur(id):
	Humeur.query.filter_by(id=id).delete()
	db.session.commit()
	return redirect(url_for('listHumeurs'))
