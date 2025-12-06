from flask import render_template, request, redirect, url_for, flash, jsonify
from webapp import webapp
from database import db
from database.models import ModerationEvent, DiscordInvite
from datetime import datetime, timedelta, timezone
from collections import Counter
from shared_stats import discord_bridge

def get_moderation_stats():
	"""Calcule les statistiques de modération"""
	events = ModerationEvent.query.all()
	
	if not events:
		return {
			'total': 0,
			'top_moderators': [],
			'type_counts': {},
			'recent_24h': 0,
			'recent_7d': 0,
			'recent_30d': 0,
			'top_sanctioned': []
		}
	
	now = datetime.now()
	
	# Comptages par modérateur
	mod_counts = Counter(e.staff_name for e in events if e.staff_name)
	top_moderators = mod_counts.most_common(5)
	
	# Comptages par type
	type_counts = Counter(e.type for e in events if e.type)
	
	# Événements récents
	recent_24h = sum(1 for e in events if e.created_at and (now - e.created_at) < timedelta(hours=24))
	recent_7d = sum(1 for e in events if e.created_at and (now - e.created_at) < timedelta(days=7))
	recent_30d = sum(1 for e in events if e.created_at and (now - e.created_at) < timedelta(days=30))
	
	# Top des utilisateurs les plus sanctionnés
	user_counts = Counter(e.username for e in events if e.username)
	top_sanctioned = user_counts.most_common(5)
	
	return {
		'total': len(events),
		'top_moderators': top_moderators,
		'type_counts': dict(type_counts),
		'recent_24h': recent_24h,
		'recent_7d': recent_7d,
		'recent_30d': recent_30d,
		'top_sanctioned': top_sanctioned
	}

@webapp.route("/moderation")
def moderation():
	events = ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).all()
	stats = get_moderation_stats()
	return render_template("moderation.html", events=events, event=None, stats=stats, 
		invites=[], invite_stats=None, guilds=[], show_invites=False, show_revoked=False)

@webapp.route("/moderation/edit/<int:event_id>")
def open_edit_moderation_event(event_id):
	event = ModerationEvent.query.get_or_404(event_id)
	events = ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).all()
	stats = get_moderation_stats()
	return render_template("moderation.html", events=events, event=event, stats=stats)

@webapp.route("/moderation/update/<int:event_id>", methods=['POST'])
def update_moderation_event(event_id):
	event = ModerationEvent.query.get_or_404(event_id)
	event.reason = request.form.get('reason')
	db.session.commit()
	return redirect(url_for('moderation'))

@webapp.route("/moderation/delete/<int:event_id>")
def delete_moderation_event(event_id):
	event = ModerationEvent.query.get_or_404(event_id)
	db.session.delete(event)
	db.session.commit()
	return redirect(url_for('moderation'))

def _make_aware(dt):
	"""Convertit un datetime naive en aware (UTC)"""
	if dt is None:
		return None
	if dt.tzinfo is None:
		return dt.replace(tzinfo=timezone.utc)
	return dt

def get_invite_stats():
	"""Calcule les statistiques des invitations"""
	invites = DiscordInvite.query.filter_by(revoked=False).all()
	
	if not invites:
		return {
			'total': 0,
			'total_uses': 0,
			'top_inviters': [],
			'permanent': 0,
			'temporary': 0,
			'expired': 0
		}
	
	now = datetime.now(timezone.utc)
	
	# Comptages par inviteur
	inviter_uses = Counter()
	for inv in invites:
		if inv.inviter_name:
			inviter_uses[inv.inviter_name] += inv.uses or 0
	top_inviters = inviter_uses.most_common(5)
	
	# Total des utilisations
	total_uses = sum(inv.uses or 0 for inv in invites)
	
	# Invitations permanentes (max_age = 0) vs temporaires
	permanent = sum(1 for inv in invites if inv.max_age == 0)
	temporary = sum(1 for inv in invites if inv.max_age > 0)
	
	# Invitations expirées (mais pas encore révoquées)
	expired = sum(1 for inv in invites if inv.expires_at and _make_aware(inv.expires_at) < now)
	
	return {
		'total': len(invites),
		'total_uses': total_uses,
		'top_inviters': top_inviters,
		'permanent': permanent,
		'temporary': temporary,
		'expired': expired
	}

def is_invite_expired(invite, now):
	"""Vérifie si une invitation est expirée"""
	if not invite.expires_at:
		return False
	expires_at = _make_aware(invite.expires_at)
	return expires_at < now

@webapp.route("/moderation/invitations")
def moderation_invitations():
	"""Affiche la liste des invitations Discord"""
	show_revoked = request.args.get('show_revoked', 'false') == 'true'
	
	query = DiscordInvite.query
	if not show_revoked:
		query = query.filter_by(revoked=False)
	
	invites = query.order_by(DiscordInvite.created_at.desc()).all()
	invite_stats = get_invite_stats()
	guilds = discord_bridge.get_guilds()
	now = datetime.now(timezone.utc)
	
	# Pré-calculer le statut expiré pour chaque invitation
	for inv in invites:
		inv.is_expired = is_invite_expired(inv, now)
	
	return render_template("moderation.html", 
		events=[], 
		event=None, 
		stats=get_moderation_stats(),
		invites=invites,
		invite_stats=invite_stats,
		guilds=guilds,
		show_invites=True,
		show_revoked=show_revoked,
		now=now
	)

@webapp.route("/moderation/invitations/sync")
def sync_invitations():
	"""Synchronise les invitations depuis Discord"""
	guild_id = request.args.get('guild_id', type=int)
	
	result = discord_bridge.sync_invites(guild_id)
	
	if result.get('success'):
		flash(f"✅ Synchronisation réussie : {result.get('synced', 0)} invitation(s) synchronisée(s)", 'success')
	else:
		flash(f"❌ Erreur : {result.get('message', 'Erreur inconnue')}", 'error')
	
	return redirect(url_for('moderation_invitations'))

@webapp.route("/moderation/invitations/revoke/<invite_code>")
def revoke_invitation(invite_code):
	"""Révoque une invitation Discord"""
	result = discord_bridge.revoke_invite(invite_code)
	
	if result.get('success'):
		flash(f"✅ Invitation {invite_code} révoquée avec succès", 'success')
	else:
		flash(f"❌ Erreur : {result.get('message', 'Erreur inconnue')}", 'error')
	
	return redirect(url_for('moderation_invitations'))

@webapp.route("/api/invitations/sync", methods=['POST'])
def api_sync_invitations():
	"""API pour synchroniser les invitations"""
	guild_id = request.json.get('guild_id') if request.is_json else None
	result = discord_bridge.sync_invites(guild_id)
	return jsonify(result)

@webapp.route("/api/invitations/revoke/<invite_code>", methods=['POST'])
def api_revoke_invitation(invite_code):
	"""API pour révoquer une invitation"""
	result = discord_bridge.revoke_invite(invite_code)
	return jsonify(result)

