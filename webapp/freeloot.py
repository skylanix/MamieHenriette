# Page webapp : configuration des notifications FreeLoot (feed LootScraper)
from flask import render_template, request, redirect, url_for
from urllib.parse import urlencode

from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.helpers import ConfigurationHelper
from discordbot import bot
from discordbot.freeloot import send_entry_to_discord_sync
from freeloot_feed import SOURCES, get_display_entries


def _format_updated(updated: str | None) -> str:
    """Formate la date ISO en affichage court."""
    if not updated:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return updated[:16] if len(updated or "") >= 16 else (updated or "")


def _parse_mention_config(raw: str | None) -> tuple[bool, bool, list[str]]:
    """Retourne (everyone, here, list of role_ids) depuis freeloot_mention."""
    everyone, here, role_ids = False, False, []
    if not raw or not str(raw).strip():
        return (everyone, here, role_ids)
    for part in str(raw).strip().split(","):
        part = part.strip()
        if part == "everyone":
            everyone = True
        elif part == "here":
            here = True
        elif part.isdigit():
            role_ids.append(part)
    return (everyone, here, role_ids)


@webapp.route("/freeloot")
@require_page("freeloot")
def openFreeLoot():
    helper = ConfigurationHelper()
    channels = bot.getAllTextChannel()
    roles = bot.getAllRoles()
    raw_sources = helper.getValue("freeloot_sources")
    enabled_sources = []
    if raw_sources and str(raw_sources).strip():
        enabled_sources = [s.strip() for s in str(raw_sources).split(",") if s.strip()]
    raw_mention = helper.getValue("freeloot_mention")
    mention_everyone, mention_here, mention_role_ids = _parse_mention_config(raw_mention)
    entries = get_display_entries()
    if enabled_sources:
        entries = [e for e in entries if e.get("source_key") in enabled_sources]
    for e in entries:
        e["updated_formatted"] = _format_updated(e.get("updated"))
    return render_template(
        "freeloot.html",
        configuration=helper,
        channels=channels,
        roles=roles,
        sources=SOURCES,
        enabled_sources=enabled_sources,
        mention_everyone=mention_everyone,
        mention_here=mention_here,
        mention_role_ids=mention_role_ids,
        entries=entries,
    )


@webapp.route("/freeloot/update", methods=["POST"])
@require_page("freeloot")
def updateFreeLoot():
    if not can_write_page("freeloot"):
        return render_template("403.html"), 403
    helper = ConfigurationHelper()
    enable = request.form.get("freeloot_enable") in ("on", "1", "true", "yes")
    channel_id = request.form.get("freeloot_channel_id")
    source_keys = request.form.getlist("freeloot_sources")
    mention_parts = []
    if request.form.get("freeloot_mention_everyone"):
        mention_parts.append("everyone")
    if request.form.get("freeloot_mention_here"):
        mention_parts.append("here")
    mention_parts.extend(request.form.getlist("freeloot_mention_roles"))
    helper.createOrUpdate("freeloot_enable", "true" if enable else "false")
    if channel_id:
        try:
            helper.createOrUpdate("freeloot_channel_id", str(int(channel_id)))
        except ValueError:
            pass
    helper.createOrUpdate("freeloot_sources", ",".join(source_keys) if source_keys else "")
    helper.createOrUpdate("freeloot_mention", ",".join(mention_parts))
    db.session.commit()
    return redirect(url_for("openFreeLoot") + "?msg=Configuration enregistrée.&type=success")


@webapp.route("/freeloot/send", methods=["POST"])
@require_page("freeloot")
def send_free_loot_to_discord():
    if not can_write_page("freeloot"):
        return render_template("403.html"), 403
    entry_id = (request.form.get("entry_id") or "").strip()
    if not entry_id:
        return redirect(url_for("openFreeLoot") + "?" + urlencode({"msg": "Entrée manquante.", "type": "error"}))
    ok, message = send_entry_to_discord_sync(bot, entry_id)
    msg_type = "success" if ok else "error"
    return redirect(url_for("openFreeLoot") + "?" + urlencode({"msg": message, "type": msg_type}))
