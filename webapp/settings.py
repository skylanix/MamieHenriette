# Paramètres webapp : rôles, permissions par page, inscriptions (super administrateur uniquement).
from flask import render_template, request, redirect, url_for, flash

from webapp import webapp
from webapp.auth import require_page
from database import db
from database.models import WebappRole, PagePermission, WebappUser
from database.helpers import ConfigurationHelper

# Métadonnées des pages : catégorie, label d'affichage, description
PAGE_METADATA = {
	"index": {
		"label": "Tableau de bord",
		"category": "general",
		"description": "Page d'accueil avec aperçu du système",
		"icon": "home"
	},
	"commandes": {
		"label": "Commandes",
		"category": "content",
		"description": "Gérer les commandes Discord et Twitch",
		"icon": "terminal"
	},
	"configurations": {
		"label": "Configurations",
		"category": "config",
		"description": "Paramètres généraux du bot",
		"icon": "settings"
	},
	"humeurs": {
		"label": "Humeurs",
		"category": "content",
		"description": "Gérer les statuts du bot Discord",
		"icon": "smile"
	},
	"protondb": {
		"label": "ProtonDB",
		"category": "content",
		"description": "Recherche de compatibilité des jeux Linux",
		"icon": "gamepad"
	},
	"live_alert": {
		"label": "Alertes Live",
		"category": "content",
		"description": "Notifications Discord pour les streams Twitch",
		"icon": "bell"
	},
	"youtube": {
		"label": "YouTube",
		"category": "content",
		"description": "Notifications Discord pour les vidéos YouTube",
		"icon": "video"
	},
	"announcements": {
		"label": "Annonces Twitch",
		"category": "content",
		"description": "Messages automatiques dans le chat Twitch",
		"icon": "megaphone"
	},
	"moderation": {
		"label": "Modération Discord",
		"category": "moderation",
		"description": "Historique de modération Discord",
		"icon": "shield"
	},
	"twitch_moderation": {
		"label": "Modération Twitch",
		"category": "moderation",
		"description": "Commandes et logs de modération Twitch",
		"icon": "shield-check"
	},
	"link_filter": {
		"label": "Filtre de liens",
		"category": "moderation",
		"description": "Filtrage automatique des liens Twitch",
		"icon": "filter"
	},
	"twitch_events": {
		"label": "Événements Twitch",
		"category": "content",
		"description": "Notifications subs, follows, raids, clips",
		"icon": "star"
	},
	"freeloot": {
		"label": "Free Loot",
		"category": "content",
		"description": "Flux RSS de jeux gratuits vers Discord",
		"icon": "gift"
	},
	"users": {
		"label": "Utilisateurs",
		"category": "admin",
		"description": "Gestion des comptes et rôles webapp",
		"icon": "users"
	},
	"settings": {
		"label": "Paramètres",
		"category": "admin",
		"description": "Rôles, permissions et inscriptions",
		"icon": "cog"
	},
}

# Labels des catégories
CATEGORY_LABELS = {
	"general": {"label": "Général", "color": "#6B7280", "icon": "layout"},
	"content": {"label": "Contenu", "color": "#3B82F6", "icon": "file-text"},
	"moderation": {"label": "Modération", "color": "#EF4444", "icon": "shield"},
	"config": {"label": "Configuration", "color": "#8B5CF6", "icon": "settings"},
	"admin": {"label": "Administration", "color": "#F59E0B", "icon": "crown"},
}

# Rôles par défaut avec métadonnées
DEFAULT_ROLES = {
	"viewer_twitch": {
		"description": "Accès minimal, consultation uniquement",
		"color": "#9146FF",
		"icon": "eye"
	},
	"utilisateur_discord": {
		"description": "Peut consulter et modifier du contenu basique",
		"color": "#5865F2",
		"icon": "user"
	},
	"moderateur_discord": {
		"description": "Accès aux outils de modération Discord",
		"color": "#57F287",
		"icon": "shield"
	},
	"expert_discord": {
		"description": "Gestion avancée du contenu et des configurations",
		"color": "#FEE75C",
		"icon": "star"
	},
	"moderateur_twitch": {
		"description": "Accès aux outils de modération Twitch",
		"color": "#9146FF",
		"icon": "shield-check"
	},
	"super_administrateur": {
		"description": "Accès complet à toutes les fonctionnalités",
		"color": "#ED4245",
		"icon": "crown"
	},
}

PAGE_KEYS = [
	("index", "Tableau de bord"),
	("configurations", "Configurations"),
	("commandes", "Commandes"),
	("humeurs", "Humeurs"),
	("live_alert", "Alerte live"),
	("announcements", "Annonces Twitch"),
	("twitch_moderation", "Modération Twitch"),
	("link_filter", "Filtre de liens"),
	("twitch_events", "Notifications événements Twitch"),
	("youtube", "YouTube"),
	("protondb", "ProtonDB"),
	("freeloot", "FreeLoot"),
	("moderation", "Modération Discord"),
	("users", "Utilisateurs"),
	("settings", "Paramètres"),
]


@webapp.route("/settings")
@require_page("settings")
def settings():
	roles = WebappRole.query.order_by(WebappRole.level).all()
	permissions = PagePermission.query.all()
	perm_by_key = {p.page_key: p for p in permissions}
	reg_enabled = ConfigurationHelper().getValue("registration_enabled") not in (None, "", "false", "0", "no", "off")
	
	# Organiser les pages par catégorie
	pages_by_category = {}
	for page_key, meta in PAGE_METADATA.items():
		category = meta.get("category", "general")
		if category not in pages_by_category:
			pages_by_category[category] = []
		pages_by_category[category].append({
			"key": page_key,
			"meta": meta,
			"permission": perm_by_key.get(page_key)
		})
	
	# Trier les pages dans chaque catégorie par label
	for category in pages_by_category:
		pages_by_category[category].sort(key=lambda x: x["meta"]["label"])
	
	return render_template(
		"settings.html",
		roles=roles,
		pages_by_category=pages_by_category,
		category_labels=CATEGORY_LABELS,
		perm_by_key=perm_by_key,
		registration_enabled=reg_enabled,
		page_metadata=PAGE_METADATA,
		default_roles_meta=DEFAULT_ROLES,
	)


@webapp.route("/settings/registration", methods=["POST"])
@require_page("settings")
def settings_toggle_registration():
	enabled = request.form.get("enabled") in ("1", "true", "on", "yes")
	ConfigurationHelper().createOrUpdate("registration_enabled", "true" if enabled else "false")
	db.session.commit()
	flash("Inscriptions " + ("activées" if enabled else "désactivées") + ".", "success")
	return redirect(url_for("settings"))


@webapp.route("/settings/roles/add", methods=["POST"])
@require_page("settings")
def settings_role_add():
	name = (request.form.get("name") or "").strip()
	level_str = request.form.get("level", "0")
	description = (request.form.get("description") or "").strip()
	color = (request.form.get("color") or "#6B7280").strip()
	icon = (request.form.get("icon") or "").strip()
	
	if not name:
		flash("Nom du rôle requis.", "error")
		return redirect(url_for("settings"))
	try:
		level = int(level_str)
	except ValueError:
		level = 0
	if WebappRole.query.filter_by(name=name).first():
		flash(f"Le rôle « {name} » existe déjà.", "error")
		return redirect(url_for("settings"))
	
	role = WebappRole(
		name=name, 
		level=level,
		description=description if description else None,
		color=color,
		icon=icon if icon else None
	)
	db.session.add(role)
	db.session.commit()
	flash(f"Rôle « {name} » créé.", "success")
	return redirect(url_for("settings"))


@webapp.route("/settings/roles/<int:role_id>/edit", methods=["POST"])
@require_page("settings")
def settings_role_edit(role_id):
	role = WebappRole.query.get_or_404(role_id)
	level_str = request.form.get("level")
	description = request.form.get("description")
	color = request.form.get("color")
	icon = request.form.get("icon")
	
	if level_str is not None:
		try:
			role.level = int(level_str)
		except ValueError:
			flash("Niveau invalide.", "error")
			return redirect(url_for("settings"))
	
	if description is not None:
		role.description = description.strip() if description.strip() else None
	if color is not None:
		role.color = color.strip() if color.strip() else "#6B7280"
	if icon is not None:
		role.icon = icon.strip() if icon.strip() else None
	
	db.session.commit()
	flash(f"Rôle « {role.name} » mis à jour.", "success")
	return redirect(url_for("settings"))


@webapp.route("/settings/roles/<int:role_id>/delete", methods=["POST"])
@require_page("settings")
def settings_role_delete(role_id):
	role = WebappRole.query.get_or_404(role_id)
	if WebappUser.query.filter_by(role=role.name).count() > 0:
		flash(f"Impossible de supprimer le rôle « {role.name} » : des utilisateurs l'utilisent.", "error")
		return redirect(url_for("settings"))
	db.session.delete(role)
	db.session.commit()
	flash(f"Rôle « {role.name} » supprimé.", "success")
	return redirect(url_for("settings"))


@webapp.route("/settings/permissions/update", methods=["POST"])
@require_page("settings")
def settings_permissions_update():
	page_key = request.form.get("page_key")
	role_name = request.form.get("role")
	if not page_key:
		return redirect(url_for("settings"))
	role = WebappRole.query.filter_by(name=role_name).first()
	level = role.level if role else 0
	perm = PagePermission.query.filter_by(page_key=page_key).first()
	if perm:
		perm.min_level = level
		perm.write_level = level
	else:
		perm = PagePermission(page_key=page_key, min_level=level, write_level=level)
		db.session.add(perm)
	db.session.commit()
	flash(f"Accès à « {page_key} » mis à jour.", "success")
	return redirect(url_for("settings"))


@webapp.route("/settings/permissions/bulk", methods=["POST"])
@require_page("settings")
def settings_permissions_bulk():
	page_keys = request.form.getlist("page_keys")
	role_name = request.form.get("role")
	if not page_keys or not role_name:
		flash("Sélectionnez au moins une page et un rôle.", "error")
		return redirect(url_for("settings"))
	role = WebappRole.query.filter_by(name=role_name).first()
	level = role.level if role else 0
	updated = 0
	for page_key in page_keys:
		perm = PagePermission.query.filter_by(page_key=page_key).first()
		if perm:
			perm.min_level = level
			perm.write_level = level
		else:
			perm = PagePermission(page_key=page_key, min_level=level, write_level=level)
			db.session.add(perm)
		updated += 1
	db.session.commit()
	flash(f"Accès mis à jour pour {updated} page(s) avec le rôle « {role_name} ».", "success")
	return redirect(url_for("settings"))
