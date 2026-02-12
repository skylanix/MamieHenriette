# Gestion des utilisateurs webapp (réservé super administrateur).
from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

from webapp import webapp
from webapp.auth import require_page
from database import db
from database.models import WebappUser, WebappRole

ROLE_LABELS = {
	"viewer_twitch": "Viewer Twitch",
	"utilisateur_discord": "Utilisateur Discord",
	"moderateur_discord": "Modérateur Discord",
	"expert_discord": "Expert Discord",
	"moderateur_twitch": "Modérateur Twitch",
	"super_administrateur": "Super administrateur",
}


def _role_labels():
	roles = WebappRole.query.order_by(WebappRole.level).all()
	return {r.name: r.name.replace("_", " ").title() for r in roles}


@webapp.route("/users")
@require_page("users")
def users_list():
	users = WebappUser.query.order_by(WebappUser.created_at.desc()).all()
	roles = WebappRole.query.order_by(WebappRole.level).all()
	labels = dict(ROLE_LABELS)
	labels.update(_role_labels())
	return render_template(
		"users.html",
		users=users,
		roles=[r.name for r in roles],
		role_labels=labels,
	)


@webapp.route("/users/role/<int:user_id>", methods=["POST"])
@require_page("users")
def users_set_role(user_id):
	user = WebappUser.query.get_or_404(user_id)
	new_role = request.form.get("role")
	existing = WebappRole.query.filter_by(name=new_role).first()
	if new_role and existing:
		user.role = new_role
		db.session.commit()
	return redirect(url_for("users_list"))


@webapp.route("/users/create", methods=["POST"])
@require_page("users")
def users_create():
	"""Création d'un utilisateur par un administrateur."""
	username = (request.form.get("username") or "").strip()
	email = (request.form.get("email") or "").strip().lower()
	password = request.form.get("password") or ""
	password_confirm = request.form.get("password_confirm") or ""
	role = request.form.get("role") or "viewer_twitch"
	
	errors = []
	
	# Validations
	if len(username) < 3:
		errors.append("Le nom d'utilisateur doit faire au moins 3 caractères.")
	if len(email) < 5 or "@" not in email:
		errors.append("Adresse e-mail invalide.")
	if len(password) < 8:
		errors.append("Le mot de passe doit faire au moins 8 caractères.")
	if password != password_confirm:
		errors.append("Les mots de passe ne correspondent pas.")
	if WebappUser.query.filter_by(username=username).first():
		errors.append("Ce nom d'utilisateur est déjà pris.")
	if WebappUser.query.filter_by(email=email).first():
		errors.append("Cette adresse e-mail est déjà utilisée.")
	
	# Vérifier que le rôle existe
	if not WebappRole.query.filter_by(name=role).first():
		errors.append("Rôle invalide.")
	
	if errors:
		for msg in errors:
			flash(msg, "error")
		return redirect(url_for("users_list"))
	
	# Créer l'utilisateur
	user = WebappUser(
		username=username,
		email=email,
		password_hash=generate_password_hash(password, method="scrypt"),
		role=role,
	)
	db.session.add(user)
	db.session.commit()
	
	flash(f"Utilisateur « {username} » créé avec succès.", "success")
	return redirect(url_for("users_list"))


@webapp.route("/users/delete/<int:user_id>", methods=["POST"])
@require_page("users")
def users_delete(user_id):
	"""Suppression d'un utilisateur (sauf soi-même)."""
	from flask_login import current_user
	
	user = WebappUser.query.get_or_404(user_id)
	
	# Protection : impossible de se supprimer soi-même
	if user.id == current_user.id:
		flash("Vous ne pouvez pas supprimer votre propre compte.", "error")
		return redirect(url_for("users_list"))
	
	username = user.username
	db.session.delete(user)
	db.session.commit()
	
	flash(f"Utilisateur « {username} » supprimé.", "success")
	return redirect(url_for("users_list"))
