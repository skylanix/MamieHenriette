from flask import render_template, request, redirect, url_for
from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import GameAlias
from database.helpers import ConfigurationHelper

@webapp.route("/protondb")
@require_page("protondb")
def openProtonDB():
	aliases = GameAlias.query.all()
	return render_template("protondb.html", aliases=aliases, configuration=ConfigurationHelper())

@webapp.route("/protondb/gamealias/add", methods=['POST'])
@require_page("protondb")
def addGameAlias():
	if not can_write_page("protondb"):
		return render_template("403.html"), 403
	game_alias = GameAlias(alias=request.form.get('alias'), name=request.form.get('name'))
	db.session.add(game_alias)
	db.session.commit()
	return redirect(url_for('openProtonDB'))

@webapp.route('/protondb/gamealias/del/<int:id>')
@require_page("protondb")
def delGameAlias(id: int):
	if not can_write_page("protondb"):
		return render_template("403.html"), 403
	GameAlias.query.filter_by(id=id).delete()
	db.session.commit()
	return redirect(url_for('openProtonDB'))

