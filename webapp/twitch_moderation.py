from flask import render_template, request, redirect, url_for, jsonify
from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import Commande, TwitchModerationLog, TwitchLinkFilter, TwitchBannedWord
from database.helpers import ConfigurationHelper
from datetime import datetime, timedelta
import asyncio

MODERATION_COMMANDS = [
    {
        "commands": ["!kick", "!to", "!timeout", "!tm"],
        "usage": "!timeout <viewer> [minutes] [raison]",
        "description": "Ejection temporaire d'un viewer (3 minutes par defaut) avec raison optionnelle",
        "permission": "Moderateur"
    },
    {
        "commands": ["!ban"],
        "usage": "!ban <viewer1> [viewer2] ...",
        "description": "Bannissement d'un ou plusieurs viewers (max 5)",
        "permission": "Moderateur"
    },
    {
        "commands": ["!unban"],
        "usage": "!unban <viewer1> [viewer2] ...",
        "description": "Debannissement d'un ou plusieurs viewers (max 5)",
        "permission": "Moderateur"
    },
    {
        "commands": ["!clean"],
        "usage": "!clean [viewer]",
        "description": "Nettoyage du chat ou des messages d'un viewer",
        "permission": "Moderateur"
    },
    {
        "commands": ["!shieldmode"],
        "usage": "!shieldmode <on/off>",
        "description": "Active/desactive le mode Shield de Twitch",
        "permission": "Moderateur"
    },
    {
        "commands": ["!settitle"],
        "usage": "!settitle <titre>",
        "description": "Changement du titre du live",
        "permission": "Moderateur"
    },
    {
        "commands": ["!setgame", "!setcateg"],
        "usage": "!setgame <jeu>",
        "description": "Changement du jeu/categorie du live",
        "permission": "Moderateur"
    },
    {
        "commands": ["!subon"],
        "usage": "!subon",
        "description": "Activation du mode abonnes uniquement",
        "permission": "Moderateur"
    },
    {
        "commands": ["!suboff"],
        "usage": "!suboff",
        "description": "Desactivation du mode abonnes uniquement",
        "permission": "Moderateur"
    },
    {
        "commands": ["!follon"],
        "usage": "!follon [minutes]",
        "description": "Activation du mode followers-only",
        "permission": "Moderateur"
    },
    {
        "commands": ["!folloff"],
        "usage": "!folloff",
        "description": "Desactivation du mode followers-only",
        "permission": "Moderateur"
    },
    {
        "commands": ["!emoteon"],
        "usage": "!emoteon",
        "description": "Activation du mode emote-only",
        "permission": "Moderateur"
    },
    {
        "commands": ["!emoteoff"],
        "usage": "!emoteoff",
        "description": "Desactivation du mode emote-only",
        "permission": "Moderateur"
    },
    {
        "commands": ["!ann"],
        "usage": "!ann <alias> <on/off/toggle>",
        "description": "Activer/desactiver/inverser une liste d'annonce par alias",
        "permission": "Moderateur"
    },
    {
        "commands": ["!no_game"],
        "usage": "!no_game <on/off>",
        "description": "Desactiver/activer tous les jeux de la chaine",
        "permission": "Moderateur"
    },
    {
        "commands": ["!multitwitch"],
        "usage": "!multitwitch [live1] [live2] ... | auto | reset",
        "description": "Creation d'un lien MultiTwitch. '@' = chaine actuelle, 'auto' = depuis le titre, 'reset' = reinitialiser",
        "permission": "Moderateur (creation) / Tous (affichage)"
    },
    {
        "commands": ["!permit"],
        "usage": "!permit <viewer> [minutes]",
        "description": "Autorise temporairement un viewer a poster un lien (1 minute par defaut)",
        "permission": "Moderateur"
    },
]

TWITCH_PERMISSIONS = {'viewer': 'Tous (viewers)', 'sub': 'Abonnés', 'vip': 'VIP', 'moderator': 'Modérateur'}


@webapp.route("/twitch-moderation")
@require_page("twitch_moderation")
def twitch_moderation():
    custom_commands = Commande.query.filter_by(twitch_enable=True).all()
    logs = TwitchModerationLog.query.order_by(TwitchModerationLog.created_at.desc()).limit(50).all()
    raw_channel = ConfigurationHelper().getValue("twitch_channel") or webapp.config["BOT_STATUS"].get("twitch_channel_name") or "chainesteve"
    twitch_channel = (raw_channel or "").strip().lower() or "chainesteve"
    embed_parent = request.host or "localhost"
    
    # Link filter status
    link_filter_config = TwitchLinkFilter.query.first()
    link_filter_enabled = link_filter_config.enabled if link_filter_config else False
    
    # Banned words
    banned_words = TwitchBannedWord.query.filter_by(enabled=True).all()
    
    # Live status (from BOT_STATUS)
    bot_status = webapp.config.get("BOT_STATUS", {})
    is_live = bot_status.get("twitch_is_live", False)
    viewer_count = bot_status.get("twitch_viewer_count", 0)
    
    return render_template(
        "twitch-moderation.html",
        commands=MODERATION_COMMANDS,
        custom_commands=custom_commands,
        logs=logs,
        twitch_permissions=TWITCH_PERMISSIONS,
        twitch_channel=twitch_channel,
        embed_parent=embed_parent,
        link_filter_enabled=link_filter_enabled,
        banned_words=banned_words,
        is_live=is_live,
        viewer_count=viewer_count,
    )

@webapp.route("/twitch-moderation/logs/clear")
@require_page("twitch_moderation")
def clear_twitch_logs():
    if not can_write_page("twitch_moderation"):
        return render_template("403.html"), 403
    TwitchModerationLog.query.delete()
    db.session.commit()
    return redirect(url_for('twitch_moderation'))

@webapp.route("/twitch-moderation/add", methods=['POST'])
@require_page("twitch_moderation")
def add_twitch_commande():
    if not can_write_page("twitch_moderation"):
        return render_template("403.html"), 403
    trigger = request.form.get('trigger')
    response = request.form.get('response')
    twitch_permission = request.form.get('twitch_permission') or 'viewer'
    if twitch_permission not in TWITCH_PERMISSIONS:
        twitch_permission = 'viewer'
    
    if trigger and response:
        if not trigger.startswith('!'):
            trigger = '!' + trigger
        
        existing = Commande.query.filter_by(trigger=trigger).first()
        if not existing:
            commande = Commande(trigger=trigger, response=response, discord_enable=False, twitch_enable=True, twitch_permission=twitch_permission)
            db.session.add(commande)
            db.session.commit()
    
    return redirect(url_for('twitch_moderation'))

@webapp.route("/twitch-moderation/banned-word/add", methods=['POST'])
@require_page("twitch_moderation")
def add_banned_word():
    if not can_write_page("twitch_moderation"):
        return render_template("403.html"), 403
    
    word = request.form.get('word', '').strip().lower()
    timeout_duration = int(request.form.get('timeout_duration', 60))
    
    if word:
        existing = TwitchBannedWord.query.filter_by(word=word).first()
        if not existing:
            banned_word = TwitchBannedWord(word=word, enabled=True, timeout_duration=timeout_duration)
            db.session.add(banned_word)
            db.session.commit()
    
    return redirect(url_for('twitch_moderation'))

@webapp.route("/twitch-moderation/banned-word/delete/<int:word_id>")
@require_page("twitch_moderation")
def delete_banned_word(word_id):
    if not can_write_page("twitch_moderation"):
        return render_template("403.html"), 403
    
    banned_word = TwitchBannedWord.query.get_or_404(word_id)
    db.session.delete(banned_word)
    db.session.commit()
    
    return redirect(url_for('twitch_moderation'))

@webapp.route("/twitch-moderation/send-message", methods=['POST'])
@require_page("twitch_moderation")
def send_twitch_message():
    if not can_write_page("twitch_moderation"):
        return jsonify({"success": False, "error": "Permission refusée"}), 403
    
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"success": False, "error": "Message vide"}), 400
    
    # Vérifier que le bot Twitch est connecté
    from twitchbot import twitchBot
    if not hasattr(twitchBot, 'chat') or not twitchBot.chat:
        return jsonify({"success": False, "error": "Bot Twitch non connecté"}), 503
    
    # Récupérer le nom du channel
    channel = ConfigurationHelper().getValue('twitch_channel')
    if not channel:
        return jsonify({"success": False, "error": "Channel Twitch non configuré"}), 400
    
    # Envoyer le message de manière asynchrone
    try:
        async def send_msg():
            try:
                await twitchBot.chat.send_message(channel, message)
                return True
            except Exception as e:
                return str(e)
        
        # Exécuter la coroutine de manière synchrone
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(send_msg())
        loop.close()
        
        if result is True:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": f"Erreur: {result}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@webapp.route("/twitch-moderation/messages")
@require_page("twitch_moderation")
def get_twitch_messages():
    """Retourne les derniers messages du chat Twitch"""
    messages = webapp.config["BOT_STATUS"].get("twitch_chat_messages", [])
    return jsonify({"messages": messages})

@webapp.route("/twitch-moderation/execute-action", methods=['POST'])
@require_page("twitch_moderation")
def execute_moderation_action():
    """Exécute une action de modération directement"""
    if not can_write_page("twitch_moderation"):
        return jsonify({"success": False, "error": "Permission refusée"}), 403
    
    data = request.get_json()
    action = data.get('action', '').strip()
    params = data.get('params', {})
    
    if not action:
        return jsonify({"success": False, "error": "Action non spécifiée"}), 400
    
    # Vérifier que le bot Twitch est connecté
    from twitchbot import twitchBot
    if not hasattr(twitchBot, 'chat') or not twitchBot.chat or not hasattr(twitchBot, 'twitch'):
        return jsonify({"success": False, "error": "Bot Twitch non connecté"}), 503
    
    # Récupérer le nom du channel
    channel = ConfigurationHelper().getValue('twitch_channel')
    if not channel:
        return jsonify({"success": False, "error": "Channel Twitch non configuré"}), 400
    
    # Créer un objet ChatMessage simulé pour les commandes qui en ont besoin
    from twitchAPI.chat import ChatMessage
    from types import SimpleNamespace
    
    # Exécuter l'action de manière asynchrone
    try:
        async def execute_action():
            try:
                if action == 'timeout':
                    from twitchbot.moderation import _get_broadcaster_id, _get_moderator_id, _get_user_id, _log_action
                    username = params.get('username', '').strip().lstrip('@')
                    duration = int(params.get('duration', 600))  # en secondes
                    reason = params.get('reason', 'Timeout')
                    
                    broadcaster_id = await _get_broadcaster_id(twitchBot.twitch, channel)
                    moderator_id = await _get_moderator_id(twitchBot.twitch)
                    user_id = await _get_user_id(twitchBot.twitch, username)
                    
                    if user_id:
                        await twitchBot.twitch.ban_user(broadcaster_id, moderator_id, user_id, reason=reason, duration=duration)
                        _log_action("timeout", "WebApp", username, f"{duration}s - {reason}")
                        return {"success": True, "message": f"Timeout de {username} pour {duration}s"}
                    return {"success": False, "error": f"Utilisateur {username} introuvable"}
                
                elif action == 'ban':
                    from twitchbot.moderation import _get_broadcaster_id, _get_moderator_id, _get_user_id, _log_action
                    username = params.get('username', '').strip().lstrip('@')
                    reason = params.get('reason', 'Ban')
                    
                    broadcaster_id = await _get_broadcaster_id(twitchBot.twitch, channel)
                    moderator_id = await _get_moderator_id(twitchBot.twitch)
                    user_id = await _get_user_id(twitchBot.twitch, username)
                    
                    if user_id:
                        await twitchBot.twitch.ban_user(broadcaster_id, moderator_id, user_id, reason=reason)
                        _log_action("ban", "WebApp", username, reason)
                        return {"success": True, "message": f"Ban de {username}"}
                    return {"success": False, "error": f"Utilisateur {username} introuvable"}
                
                elif action == 'clean':
                    from twitchbot.moderation import _get_broadcaster_id, _get_moderator_id, _get_user_id, _log_action
                    username = params.get('username', '').strip().lstrip('@')
                    
                    broadcaster_id = await _get_broadcaster_id(twitchBot.twitch, channel)
                    moderator_id = await _get_moderator_id(twitchBot.twitch)
                    
                    if username:
                        user_id = await _get_user_id(twitchBot.twitch, username)
                        if user_id:
                            await twitchBot.twitch.delete_chat_messages(broadcaster_id, moderator_id, user_id=user_id)
                            _log_action("clean", "WebApp", username)
                            return {"success": True, "message": f"Messages de {username} supprimés"}
                        return {"success": False, "error": f"Utilisateur {username} introuvable"}
                    else:
                        await twitchBot.twitch.delete_chat_messages(broadcaster_id, moderator_id)
                        _log_action("clean", "WebApp", None, "Chat complet")
                        return {"success": True, "message": "Chat nettoyé"}
                
                elif action == 'permit':
                    from database.models import TwitchPermit
                    username = params.get('username', '').strip().lstrip('@').lower()
                    duration = int(params.get('duration', 60))  # en secondes
                    
                    expires_at = datetime.now() + timedelta(seconds=duration)
                    
                    with webapp.app_context():
                        existing = TwitchPermit.query.filter_by(username=username).first()
                        if existing:
                            existing.expires_at = expires_at
                        else:
                            permit = TwitchPermit(username=username, expires_at=expires_at)
                            db.session.add(permit)
                        db.session.commit()
                    
                    return {"success": True, "message": f"Permit accordé à {username} pour {duration//60}min"}
                
                elif action in ['subon', 'suboff', 'emoteon', 'emoteoff']:
                    from twitchbot.moderation import _get_broadcaster_id, _get_moderator_id, _log_action
                    
                    broadcaster_id = await _get_broadcaster_id(twitchBot.twitch, channel)
                    moderator_id = await _get_moderator_id(twitchBot.twitch)
                    
                    if action == 'subon':
                        await twitchBot.twitch.update_chat_settings(broadcaster_id, moderator_id, subscriber_mode=True)
                        _log_action("subon", "WebApp")
                        return {"success": True, "message": "Mode abonnés activé"}
                    elif action == 'suboff':
                        await twitchBot.twitch.update_chat_settings(broadcaster_id, moderator_id, subscriber_mode=False)
                        _log_action("suboff", "WebApp")
                        return {"success": True, "message": "Mode abonnés désactivé"}
                    elif action == 'emoteon':
                        await twitchBot.twitch.update_chat_settings(broadcaster_id, moderator_id, emote_mode=True)
                        _log_action("emoteon", "WebApp")
                        return {"success": True, "message": "Mode emote activé"}
                    elif action == 'emoteoff':
                        await twitchBot.twitch.update_chat_settings(broadcaster_id, moderator_id, emote_mode=False)
                        _log_action("emoteoff", "WebApp")
                        return {"success": True, "message": "Mode emote désactivé"}
                
                return {"success": False, "error": f"Action '{action}' non reconnue"}
                
            except Exception as e:
                import logging
                logging.error(f"Erreur lors de l'exécution de l'action {action}: {e}")
                return {"success": False, "error": str(e)}
        
        # Exécuter la coroutine de manière synchrone
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(execute_action())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
