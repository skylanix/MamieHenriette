# Module partagé : récupération et parsing du flux LootScraper (sans dépendance Discord)
import re
import xml.etree.ElementTree as ET
from html import unescape

import requests

FEED_URL = "https://feed.eikowagenknecht.com/lootscraper.xml"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

SOURCES = [
    ("epic_pc", "Epic Games (PC)", "🖥️"),
    ("epic_android", "Epic Games (Android)", "🤖"),
    ("epic_ios", "Epic Games (iOS)", "🍎"),
    ("amazon_prime", "Amazon Prime Gaming", "📦"),
    ("gog", "GOG", "🎮"),
    ("google_play", "Google Play", "🤖"),
    ("apple_app_store", "Apple App Store", "🍎"),
]


def source_key_from_entry(title: str, link: str) -> str | None:
    """Détermine la clé source+plateforme depuis le titre et le lien."""
    title_upper = (title or "").upper()
    link_lower = (link or "").lower()
    if "EPIC GAMES" in title_upper:
        if "-ios-" in link_lower or "/ios-" in link_lower:
            return "epic_ios"
        if "-android-" in link_lower or "/android-" in link_lower:
            return "epic_android"
        return "epic_pc"
    if "AMAZON PRIME" in title_upper:
        return "amazon_prime"
    if "GOG" in title_upper:
        return "gog"
    if "GOOGLE PLAY" in title_upper:
        return "google_play"
    if "APPLE APP STORE" in title_upper:
        return "apple_app_store"
    return None


def game_name_from_title(title: str) -> str:
    """Extrait le nom du jeu depuis le titre."""
    if not title:
        return "Jeu gratuit"
    for prefix in (
        "Epic Games (Game) - ",
        "Amazon Prime (Game) - ",
        "GOG (Game) - ",
        "GOG (Game, Always Free) - ",
        "Google Play (Game) - ",
        "Apple App Store (Game) - ",
    ):
        if title.startswith(prefix):
            return unescape(title[len(prefix) :].strip())
    if " - " in title:
        return unescape(title.split(" - ", 1)[1].strip())
    return unescape(title.strip())


def extract_image_from_content(content: str) -> str | None:
    """Extrait l'URL de la première image du contenu HTML (toutes balises img)."""
    if not content:
        return None

    def _normalize_url(url: str) -> str:
        u = unescape(url.strip()).replace("&amp;", "&")
        return u

    # 1) Balises <img ... src="url" ...>
    for m in re.finditer(r'<img[^>]+src\s*=\s*["\']([^"\']+)["\']', content, re.I):
        url = _normalize_url(m.group(1))
        if url.startswith("http"):
            return url
    # 2) Fallback: toute attribution src="http..." (certains CDN n'ont pas d'extension)
    for m in re.finditer(r'src\s*=\s*["\'](https?://[^"\']{20,})["\']', content, re.I):
        url = _normalize_url(m.group(1))
        if url.startswith("http"):
            return url
    return None


def extract_description_from_content(content: str, max_len: int = 400) -> str | None:
    """Extrait la description du jeu depuis le contenu HTML (balise <b>Description:</b>)."""
    if not content:
        return None
    m = re.search(r"<b>Description:</b>\s*([^<]+)", content, re.I | re.DOTALL)
    if not m:
        return None
    desc = unescape(m.group(1).strip())
    desc = re.sub(r"\s+", " ", desc)
    if len(desc) > max_len:
        desc = desc[: max_len - 3].rsplit(" ", 1)[0] + "..."
    return desc or None


def extract_valid_to_from_content(content: str) -> str | None:
    """Extrait la date 'Offer valid to' depuis le contenu HTML."""
    if not content:
        return None
    m = re.search(r"<b>Offer valid to:</b>\s*(\d{4}-\d{2}-\d{2}[^<]*)", content, re.I)
    return m.group(1).strip() if m else None


def extract_recommended_price_from_content(content: str) -> str | None:
    """Extrait le prix recommandé (ex: '39.99 EUR') depuis le contenu HTML."""
    if not content:
        return None
    m = re.search(r"<b>Recommended price\s*\([^)]*\):\s*</b>\s*([^<]+)", content, re.I)
    if not m:
        m = re.search(r"Recommended price[^<]*</b>\s*([^<]+)", content, re.I)
    return unescape(m.group(1).strip()) if m else None


def extract_genres_from_content(content: str) -> str | None:
    """Extrait les genres (ex: 'Action, Indie') depuis le contenu HTML."""
    if not content:
        return None
    m = re.search(r"<b>Genres:</b>\s*([^<]+)", content, re.I)
    return unescape(m.group(1).strip()) if m else None


def extract_rating_from_content(content: str) -> str | None:
    """Extrait le rating (texte après Ratings:, liens ou texte brut)."""
    if not content:
        return None
    m = re.search(r"<b>Ratings:</b>\s*(.+?)</li>", content, re.I | re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    raw = re.sub(r"<a[^>]*>([^<]*)</a>", r"\1", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = unescape(re.sub(r"\s+", " ", raw).strip())
    return raw if len(raw) > 0 and len(raw) < 200 else None


def fetch_feed() -> list[dict] | None:
    """Récupère et parse le flux Atom, retourne une liste d'entrées brutes."""
    try:
        r = requests.get(FEED_URL, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        entries = []
        for entry_el in root.findall(".//atom:entry", ATOM_NS):
            entry_id_el = entry_el.find("atom:id", ATOM_NS)
            title_el = entry_el.find("atom:title", ATOM_NS)
            link_el = entry_el.find("atom:link", ATOM_NS)
            content_el = entry_el.find("atom:content", ATOM_NS)
            updated_el = entry_el.find("atom:updated", ATOM_NS) or entry_el.find("atom:published", ATOM_NS)
            entry_id = entry_id_el.text.strip() if entry_id_el is not None and entry_id_el.text else None
            title = title_el.text.strip() if title_el is not None and title_el.text else None
            link = link_el.get("href") if link_el is not None else None
            content = ""
            if content_el is not None:
                # Sérialiser tout le sous-arbre pour ne rien perdre (notamment les <img>)
                content = ET.tostring(content_el, encoding="unicode", method="xml")
                # Normaliser les préfixes de namespace (ex: <html:b> -> <b>) pour que les regex d'extraction matchent
                content = content.replace("</html:", "</").replace("<html:", "<")
            updated = updated_el.text.strip() if updated_el is not None and updated_el.text else None
            if entry_id and title:
                entries.append({
                    "id": entry_id,
                    "title": title,
                    "link": link or "",
                    "content": content or "",
                    "updated": updated,
                })
        return entries
    except Exception:
        return None


def get_display_entries() -> list[dict]:
    """Retourne la liste des entrées formatées pour affichage (webapp)."""
    raw = fetch_feed()
    if not raw:
        return []
    result = []
    for e in raw:
        sk = source_key_from_entry(e["title"], e["link"])
        content = e.get("content") or ""
        desc = extract_description_from_content(content)
        result.append({
            "id": e["id"],
            "title": e["title"],
            "link": e["link"],
            "game_name": game_name_from_title(e["title"]),
            "source_key": sk or "other",
            "source_label": next((s[1] for s in SOURCES if s[0] == sk), sk or "Autre"),
            "emoji": next((s[2] for s in SOURCES if s[0] == sk), "🎁"),
            "image_url": extract_image_from_content(content),
            "description": desc,
            "valid_to": extract_valid_to_from_content(content),
            "recommended_price": extract_recommended_price_from_content(content),
            "genres": extract_genres_from_content(content),
            "rating": extract_rating_from_content(content),
            "updated": e.get("updated"),
        })
    return result
