from flask import render_template, request, redirect, url_for
from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import Humeur

@webapp.route("/humeurs")
@require_page("humeurs")
def listHumeurs():
	humeurs = Humeur.query.all()
	return render_template("humeurs.html", humeurs=humeurs)

@webapp.route('/humeurs/add', methods=['POST'])
@require_page("humeurs")
def addHumeur():
	if not can_write_page("humeurs"):
		return render_template("403.html"), 403
	humeur = Humeur(text=request.form['text'])
	db.session.add(humeur)
	db.session.commit()
	return redirect(url_for('listHumeurs'))

@webapp.route('/humeurs/del/<id>')
@require_page("humeurs")
def delHumeur(id):
	if not can_write_page("humeurs"):
		return render_template("403.html"), 403
	Humeur.query.filter_by(id=id).delete()
	db.session.commit()
	return redirect(url_for('listHumeurs'))
