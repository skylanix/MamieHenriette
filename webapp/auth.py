# Authentification webapp : login, register, logout et contrôle d'accès par rôles.
from functools import wraps

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from database import db
from database.models import WebappUser, ROLE_ORDER, PagePermission
from database.helpers import ConfigurationHelper

from webapp import webapp


def require_roles(allowed_roles: list):
	"""Décorateur : exige que l'utilisateur soit authentifié et ait l'un des rôles autorisés."""
	def decorator(f):
		@wraps(f)
		def wrapped(*args, **kwargs):
			if not current_user.is_authenticated:
				return redirect(url_for("login", next=request.url))
			if current_user.role not in allowed_roles:
				return render_template("403.html"), 403
			return f(*args, **kwargs)
		return wrapped
	return decorator


def require_role_min(min_role: str):
	"""Décorateur : exige que l'utilisateur ait au moins le rôle min_role (niveau en base)."""
	def decorator(f):
		@wraps(f)
		def wrapped(*args, **kwargs):
			if not current_user.is_authenticated:
				return redirect(url_for("login", next=request.url))
			if not current_user.has_role_at_least(min_role):
				return render_template("403.html"), 403
			return f(*args, **kwargs)
		return wrapped
	return decorator


def _page_min_level(page_key: str, for_write: bool = False) -> int:
	"""Niveau minimum requis pour la page (lecture ou écriture)."""
	perm = PagePermission.query.filter_by(page_key=page_key).first()
	if not perm:
		return 0
	if for_write and perm.write_level is not None:
		return perm.write_level
	return perm.min_level


def require_page(page_key: str):
	"""Décorateur : accès en lecture selon les permissions de la page (webapp_page_permission)."""
	def decorator(f):
		@wraps(f)
		def wrapped(*args, **kwargs):
			if not current_user.is_authenticated:
				return redirect(url_for("login", next=request.url))
			min_level = _page_min_level(page_key, for_write=False)
			if not current_user.has_level_at_least(min_level):
				return render_template("403.html"), 403
			return f(*args, **kwargs)
		return wrapped
	return decorator


def require_page_write(page_key: str):
	"""Décorateur : accès en écriture selon les permissions de la page."""
	def decorator(f):
		@wraps(f)
		def wrapped(*args, **kwargs):
			if not current_user.is_authenticated:
				return redirect(url_for("login", next=request.url))
			min_level = _page_min_level(page_key, for_write=True)
			if not current_user.has_level_at_least(min_level):
				return render_template("403.html"), 403
			return f(*args, **kwargs)
		return wrapped
	return decorator


def can_write_page(page_key: str) -> bool:
	"""Retourne True si l'utilisateur connecté a le niveau pour écrire sur cette page."""
	if not current_user.is_authenticated:
		return False
	return current_user.has_level_at_least(_page_min_level(page_key, for_write=True))


@webapp.route("/login", methods=["GET", "POST"])
def login():
	if current_user.is_authenticated:
		return redirect(url_for("index"))
	if request.method == "POST":
		identifier = (request.form.get("identifier") or "").strip()
		password = request.form.get("password") or ""
		if not identifier or not password:
			flash("Identifiant et mot de passe requis.", "error")
			return render_template("login.html")
		user = WebappUser.query.filter(
			(WebappUser.username == identifier) | (WebappUser.email == identifier)
		).first()
		if user and check_password_hash(user.password_hash, password):
			login_user(user, remember=True)
			next_url = request.args.get("next")
			if next_url and next_url.startswith("/"):
				return redirect(next_url)
			return redirect(url_for("index"))
		flash("Identifiant ou mot de passe incorrect.", "error")
		return render_template("login.html")
	return render_template("login.html")


@webapp.route("/register", methods=["GET", "POST"])
def register():
	if current_user.is_authenticated:
		return redirect(url_for("index"))
	# Inscriptions désactivées par le super admin
	reg_enabled = ConfigurationHelper().getValue("registration_enabled")
	if reg_enabled in (None, "", "false", "0", "no", "off"):
		flash("Les inscriptions sont désactivées.", "error")
		return redirect(url_for("login"))
	if request.method == "POST":
		username = (request.form.get("username") or "").strip()
		email = (request.form.get("email") or "").strip().lower()
		password = request.form.get("password") or ""
		password_confirm = request.form.get("password_confirm") or ""
		errors = []
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
		if errors:
			for msg in errors:
				flash(msg, "error")
			return render_template("register.html")
		# Premier inscrit = super administrateur
		role = "super_administrateur" if WebappUser.query.count() == 0 else "viewer_twitch"
		user = WebappUser(
			username=username,
			email=email,
			password_hash=generate_password_hash(password, method="scrypt"),
			role=role,
		)
		db.session.add(user)
		db.session.commit()
		flash("Compte créé. Vous pouvez vous connecter.", "success")
		return redirect(url_for("login"))
	return render_template("register.html")


@webapp.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect(url_for("login"))
