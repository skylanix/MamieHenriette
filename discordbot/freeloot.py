# FreeLoot Discord : notifications depuis le feed LootScraper (jeux gratuits Epic, Amazon Prime, GOG, etc.)
import asyncio
import logging

from discord import Client
from database import db
from database.helpers import ConfigurationHelper
from database.models import FreeLootEntry
from freeloot_feed import (
    SOURCES,
    fetch_feed,
    source_key_from_entry,
    game_name_from_title,
    extract_image_from_content,
    extract_description_from_content,
    extract_valid_to_from_content,
    extract_recommended_price_from_content,
    extract_genres_from_content,
    extract_rating_from_content,
)


def _get_mention_content() -> str:
    """Construit le contenu du message (mentions) depuis la config."""
    raw = ConfigurationHelper().getValue("freeloot_mention")
    if not raw or not str(raw).strip():
        return ""
    parts = []
    for s in str(raw).strip().split(","):
        s = s.strip()
        if s == "everyone":
            parts.append("@everyone")
        elif s == "here":
            parts.append("@here")
        elif s.isdigit():
            parts.append(f"<@&{s}>")
    return " ".join(parts) if parts else ""


def _is_enabled_source(source_key: str) -> bool:
    """Vérifie si cette source est activée dans la config (freeloot_sources)."""
    raw = ConfigurationHelper().getValue("freeloot_sources")
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return True
    enabled = [s.strip() for s in str(raw).split(",") if s.strip()]
    return source_key in enabled if enabled else True


def _store_label_for_title(source_key: str) -> str:
    """Libellé court pour le titre style DraftBot (ex: 'l'Epic Games Store')."""
    labels = {
        "epic_pc": "l'Epic Games Store",
        "epic_android": "l'Epic Games Store (Android)",
        "epic_ios": "l'Epic Games Store (iOS)",
        "amazon_prime": "Amazon Prime Gaming",
        "gog": "GOG",
        "google_play": "Google Play",
        "apple_app_store": "l'App Store",
    }
    return labels.get(source_key, "la boutique")


# Logo (thumbnail) de chaque boutique pour l'embed Discord (affiché en haut à droite)
SOURCE_LOGO_URLS = {
    "epic_pc": "https://store.epicgames.com/favicon.ico",
    "epic_android": "https://store.epicgames.com/favicon.ico",
    "epic_ios": "https://store.epicgames.com/favicon.ico",
    "amazon_prime": "https://gaming.amazon.com/favicon.ico",
    "gog": "https://www.gog.com/favicon.ico",
    "google_play": "https://play.google.com/favicon.ico",
    "apple_app_store": "https://www.apple.com/favicon.ico",
}


def _build_embed(entry: dict, source_key: str):
    import discord
    game_name = game_name_from_title(entry["title"])
    source_label = next((s[1] for s in SOURCES if s[0] == source_key), source_key)
    link = entry.get("link") or ""
    content_raw = entry.get("content") or ""
    img_url = extract_image_from_content(content_raw)
    description = extract_description_from_content(content_raw, max_len=350)
    valid_to = extract_valid_to_from_content(content_raw)
    store_title = _store_label_for_title(source_key)
    # Couleur barre gauche style DraftBot (orange-rouge)
    color = 0xE67E22
    title = f"{game_name} gratuit sur {store_title} !"
    embed = discord.Embed(
        title=title,
        url=link if link.startswith("http") else None,
        color=color,
    )
    if description:
        embed.description = description
    # Prix / gratuit / validité (Discord : pas de couleur dans le texte, seulement **gras** / markdown)
    value_parts = ["**Gratuit**"]
    if valid_to:
        try:
            from datetime import datetime
            end = datetime.fromisoformat(valid_to.replace("Z", "+00:00"))
            value_parts.append(f"jusqu'au {end.strftime('%d/%m/%Y')}")
        except Exception:
            value_parts.append(f"jusqu'au {valid_to[:10]}")
    embed.add_field(
        name="Prix",
        value=" • ".join(value_parts),
        inline=False,
    )
    recommended_price = extract_recommended_price_from_content(content_raw)
    if recommended_price:
        embed.add_field(name="Prix recommandé", value=recommended_price, inline=True)
    genres = extract_genres_from_content(content_raw)
    if genres:
        embed.add_field(name="Genres", value=genres, inline=True)
    rating = extract_rating_from_content(content_raw)
    if rating:
        embed.add_field(name="Ratings", value=rating, inline=True)
    if link and link.startswith("http"):
        embed.add_field(
            name="\u200b",
            value=f"[Ouvrir dans la boutique !]({link})",
            inline=False,
        )
    # Thumbnail (logo de la boutique en haut à droite)
    logo_url = SOURCE_LOGO_URLS.get(source_key)
    if logo_url and logo_url.startswith("http"):
        embed.set_thumbnail(url=logo_url)
    # Image principale (style DraftBot)
    if img_url and img_url.startswith("http"):
        embed.set_image(url=img_url)
    embed.set_footer(text="MamieHenriette • FreeLoot")
    return embed


_freeloot_first_check = True

async def checkFreeLootAndNotify(bot: Client):
    global _freeloot_first_check
    helper = ConfigurationHelper()
    if not helper.getValue("freeloot_enable"):
        return
    channel_id = helper.getIntValue("freeloot_channel_id")
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if not channel:
        logging.warning("FreeLoot: canal Discord introuvable")
        return
    entries = fetch_feed()
    if not entries:
        return
    
    # Au premier check après le démarrage, on synchronise sans notifier
    if _freeloot_first_check:
        logging.info("FreeLoot: première vérification, synchronisation sans notification")
        for entry in entries:
            entry_id = entry["id"]
            if not FreeLootEntry.query.get(entry_id):
                source_key = source_key_from_entry(entry["title"], entry["link"])
                if source_key and _is_enabled_source(source_key):
                    try:
                        db.session.add(FreeLootEntry(entry_id=entry_id))
                        db.session.commit()
                    except Exception as e:
                        logging.error(f"FreeLoot: erreur de synchronisation pour {entry_id}: {e}")
                        db.session.rollback()
        _freeloot_first_check = False
        return
    
    # Vérifications suivantes : notification normale
    for entry in entries:
        entry_id = entry["id"]
        if FreeLootEntry.query.get(entry_id):
            continue
        source_key = source_key_from_entry(entry["title"], entry["link"])
        if not source_key or not _is_enabled_source(source_key):
            continue
        try:
            embed = _build_embed(entry, source_key)
            content = _get_mention_content()
            await channel.send(content=content or None, embed=embed)
            db.session.add(FreeLootEntry(entry_id=entry_id))
            db.session.commit()
        except Exception as e:
            logging.error(f"FreeLoot: envoi Discord échoué pour {entry_id}: {e}")
            db.session.rollback()


async def _send_entry_to_discord_async(bot: Client, entry_id: str) -> tuple[bool, str]:
    """
    Envoie une entrée FreeLoot sur Discord (appel manuel). Retourne (succès, message).
    """
    channel_id = ConfigurationHelper().getIntValue("freeloot_channel_id")
    if not channel_id:
        return (False, "Aucun canal Discord configuré pour FreeLoot.")
    channel = bot.get_channel(channel_id)
    if not channel:
        return (False, "Canal Discord introuvable.")
    entries = fetch_feed()
    if not entries:
        return (False, "Impossible de charger le flux.")
    entry = next((e for e in entries if e.get("id") == entry_id), None)
    if not entry:
        return (False, "Entrée introuvable dans le flux.")
    source_key = source_key_from_entry(entry["title"], entry["link"])
    if not source_key:
        return (False, "Source non reconnue pour cette entrée.")
    try:
        embed = _build_embed(entry, source_key)
        content = _get_mention_content()
        await channel.send(content=content or None, embed=embed)
        if not FreeLootEntry.query.get(entry_id):
            db.session.add(FreeLootEntry(entry_id=entry_id))
            db.session.commit()
        return (True, "Annonce envoyée sur Discord.")
    except Exception as e:
        logging.error(f"FreeLoot: envoi manuel échoué pour {entry_id}: {e}")
        db.session.rollback()
        return (False, str(e))


def send_entry_to_discord_sync(bot: Client, entry_id: str) -> tuple[bool, str]:
    """Appel synchrone pour envoyer une entrée sur Discord (depuis la webapp)."""
    try:
        future = asyncio.run_coroutine_threadsafe(
            _send_entry_to_discord_async(bot, entry_id),
            bot.loop,
        )
        return future.result(timeout=15)
    except Exception as e:
        logging.error(f"FreeLoot: send_entry_to_discord_sync: {e}")
        return (False, str(e))
