"""
SENTINEL OSINT - APEX ENGINE v20.0
Maximum Data Retrieval / Zero Blind Spots
Every legal vector exploited.
"""

import asyncio
import hashlib
import re
import io
from typing import List, Dict, Any
from datetime import datetime
import httpx
from loguru import logger

from app.workers.celery_app import celery_app
from app.config import settings

# ============================================================
# BLACKLISTS & CONFIG
# ============================================================
HOLEHE_BLACKLIST = {"naturabuy", "duolingo", "instagram", "snapchat", "pinterest",
                    "xnxx", "pornhub", "xvideos", "redtube"}

PLATFORMS = [
    # === SOCIAL (15) ===
    ("GitHub", "https://github.com/{u}", "coding"),
    ("Twitter/X", "https://x.com/{u}", "social"),
    ("Reddit", "https://reddit.com/user/{u}", "social"),
    ("TikTok", "https://tiktok.com/@{u}", "social"),
    ("YouTube", "https://youtube.com/@{u}", "social"),
    ("LinkedIn", "https://linkedin.com/in/{u}", "professional"),
    ("Facebook", "https://facebook.com/{u}", "social"),
    ("Pinterest", "https://pinterest.com/{u}", "social"),
    ("Twitch", "https://twitch.tv/{u}", "gaming"),
    ("VK", "https://vk.com/{u}", "social"),
    ("Telegram", "https://t.me/{u}", "social"),
    ("Mastodon", "https://mastodon.social/@{u}", "social"),
    ("Threads", "https://threads.net/@{u}", "social"),
    ("Bluesky", "https://bsky.app/profile/{u}", "social"),
    ("Rumble", "https://rumble.com/user/{u}", "social"),

    # === CODING & TECH (12) ===
    ("GitLab", "https://gitlab.com/{u}", "coding"),
    ("Medium", "https://medium.com/@{u}", "professional"),
    ("HackerNews", "https://news.ycombinator.com/user?id={u}", "tech"),
    ("ProductHunt", "https://producthunt.com/@{u}", "tech"),
    ("CodePen", "https://codepen.io/{u}", "coding"),
    ("HackerOne", "https://hackerone.com/{u}", "professional"),
    ("Replit", "https://replit.com/@{u}", "coding"),
    ("NPM", "https://www.npmjs.com/~{u}", "coding"),
    ("PyPI", "https://pypi.org/user/{u}", "coding"),
    ("Docker Hub", "https://hub.docker.com/u/{u}", "coding"),
    ("Keybase", "https://keybase.io/{u}", "tech"),
    ("About.me", "https://about.me/{u}", "professional"),

    # === CREATIVE (8) ===
    ("Behance", "https://behance.net/{u}", "creative"),
    ("Dribbble", "https://dribbble.com/{u}", "creative"),
    ("SoundCloud", "https://soundcloud.com/{u}", "creative"),
    ("Spotify", "https://open.spotify.com/user/{u}", "creative"),
    ("Flickr", "https://flickr.com/people/{u}", "creative"),
    ("Vimeo", "https://vimeo.com/{u}", "creative"),
    ("DeviantArt", "https://deviantart.com/{u}", "creative"),
    ("ArtStation", "https://artstation.com/{u}", "creative"),

    # === FINANCE (4) ===
    ("CashApp", "https://cash.app/${u}", "finance"),
    ("Venmo", "https://venmo.com/u/{u}", "finance"),
    ("Patreon", "https://patreon.com/{u}", "finance"),
    ("BuyMeACoffee", "https://buymeacoffee.com/{u}", "finance"),

    # === PROFESSIONAL (5) ===
    ("Fiverr", "https://fiverr.com/{u}", "professional"),
    ("Upwork", "https://upwork.com/freelancers/~{u}", "professional"),
    ("Freelancer", "https://freelancer.com/u/{u}", "professional"),
    ("Gravatar", "https://en.gravatar.com/{u}", "professional"),
    ("Linktree", "https://linktr.ee/{u}", "professional"),

    # === GAMING (8) ===
    ("Steam", "https://steamcommunity.com/id/{u}", "gaming"),
    ("Roblox", "https://roblox.com/user.aspx?username={u}", "gaming"),
    ("Chess.com", "https://chess.com/member/{u}", "gaming"),
    ("Lichess", "https://lichess.org/@/{u}", "gaming"),
    ("MyAnimeList", "https://myanimelist.net/profile/{u}", "gaming"),
    ("Xbox Gamertag", "https://xboxgamertag.com/search/{u}", "gaming"),
    ("Fortnite Tracker", "https://fortnitetracker.com/profile/all/{u}", "gaming"),
    ("Clash Royale", "https://royaleapi.com/player/{u}", "gaming"),

    # === SOCIAL MISC (6) ===
    ("Strava", "https://strava.com/athletes/{u}", "lifestyle"),
    ("Goodreads", "https://goodreads.com/user/show/{u}", "lifestyle"),
    ("Letterboxd", "https://letterboxd.com/{u}", "lifestyle"),
    ("Quora", "https://quora.com/profile/{u}", "social"),
    ("Slideshare", "https://slideshare.net/{u}", "professional"),
    ("Instructables", "https://instructables.com/member/{u}", "lifestyle"),

    # === DATING (4) ===
    ("OKCupid", "https://okcupid.com/profile/{u}", "dating"),
    ("Tinder (web)", "https://tinder.com/@{u}", "dating"),
    ("Bumble (web)", "https://bumble.com/en-us/profile/{u}", "dating"),
    ("Plenty of Fish", "https://pof.com/viewprofile.aspx?profile_id={u}", "dating"),

    # === MARKETPLACE (4) ===
    ("eBay", "https://ebay.com/usr/{u}", "marketplace"),
    ("Etsy", "https://etsy.com/shop/{u}", "marketplace"),
    ("Mercari", "https://www.mercari.com/u/{u}", "marketplace"),
    ("Vinted", "https://www.vinted.fr/member/{u}", "marketplace"),
]

import redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

# ============================================================
# URL CHECKER (Deep Profiling & False-Positive Elimination)
# ============================================================
async def check_url(client: httpx.AsyncClient, name: str, url: str, category: str):
    try:
        redis_client.publish("sentinel_logs", f'{{"module":"pivot", "platform":"{name}", "status":"SCANNING"}}')
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        # Passage en mode GET au lieu de HEAD pour lire le code HTML (Combat les Faux Positifs SPA)
        resp = await client.get(url, headers=headers, timeout=6.0)
        
        if resp.status_code == 200:
            final = str(resp.url).lower()
            # 1. Filtre par l'URL finale (Redirections furtives vers la page d'accueil ou de login)
            if any(x in final for x in ["login", "signup", "error", "notfound", "404", "auth", "welcome"]):
                redis_client.publish("sentinel_logs", f'{{"module":"pivot", "platform":"{name}", "status":"NOT_FOUND"}}')
                return None
                
            # 2. IA d'analyse sémantique du HTML (Détecte les 404 "déguisées" en 200 OK)
            text = resp.text.lower()
            false_positive_flags = [
                "page not found", "this page doesn't exist", "doesn't exist", "not found",
                "could not be found", "utilisateur introuvable", "page introuvable",
                "this account doesn't exist", "account has been suspended", "profile not found",
                "nobody here", "no such user", "404 -", "<title>404", "error 404",
                "nothing to see here", "account deleted", "no results"
            ]
            
            for flag in false_positive_flags:
                if flag in text:
                    redis_client.publish("sentinel_logs", f'{{"module":"pivot", "platform":"{name}", "status":"NOT_FOUND"}}')
                    return None  # C'est un Faux Positif avéré
            
            redis_client.publish("sentinel_logs", f'{{"module":"pivot", "platform":"{name}", "status":"FOUND"}}')
            # Formattage de la validation
            return {"source": name, "category": category,
                    "title": f"Profil vérifié: {name}", "url": url,
                    "snippet": f"Compte public trouvé et audité sur {name} [{category}]. Code 200 OK sans erreur HTML.",
                    "confidence": 0.98}
    except Exception: pass
    redis_client.publish("sentinel_logs", f'{{"module":"pivot", "platform":"{name}", "status":"FAILED"}}')
    return None

def extract_french_zipcode(query: str) -> str:
    # Détecte un code postal français à 5 chiffres dans le pseudo (ex: john75011)
    match = re.search(r'(?<!\d)(0[1-9]|[1-8]\d|9[0-5]|97[1-6]|98[46-8])\d{3}(?!\d)', query)
    if match:
        zip_str = match.group(0)
        dept = zip_str[:2]
        regions = {
            "75": "Paris", "13": "Marseille", "69": "Lyon", "31": "Toulouse", "06": "Nice",
            "44": "Nantes", "34": "Montpellier", "67": "Strasbourg", "33": "Bordeaux", "59": "Lille",
            "35": "Rennes", "51": "Reims", "42": "Saint-Étienne", "83": "Toulon", "76": "Le Havre / Rouen",
            "38": "Grenoble", "21": "Dijon", "49": "Angers", "97": "Outre-Mer", "93": "Seine-Saint-Denis",
            "92": "Hauts-de-Seine", "94": "Val-de-Marne", "78": "Yvelines", "91": "Essonne", "77": "Seine-et-Marne"
        }
        city = regions.get(dept, f"Département {dept}")
        return f"Code postal {zip_str} suspecté ({city}, France)."
    
    # Filtre les départements à 2 chiffres
    match2 = re.search(r'(?<!\d)(0[1-9]|[1-8]\d|9[0-5])(?!\d)', query)
    if match2:
        dept = match2.group(0)
        if len(query) > 5: # john75 vs 75
            return f"Suffixe '{dept}' détecté. Cible possiblement liée au département {dept} (FR)."
    return ""

# ============================================================
# AI PROFILING ENGINE
# ============================================================
def generate_ai_profile(results: List[Dict], query: str) -> Dict[str, Any]:
    categories = [r.get("category","") for r in results if isinstance(r, dict)]
    score = min((len(results) - 1) * 12.5, 100) # -1 pour ne pas compter le profil lui-meme
    threat = "LOW" if score < 40 else ("MEDIUM" if score < 70 else "HIGH" if score < 90 else "CRITICAL")
    
    insights = []
    
    # GEO-INFERENCE LOGIC (A la demande de l'utilisateur)
    geo_intel = extract_french_zipcode(query)
    if geo_intel:
        insights.append(f"📍 GEO-INTEL: {geo_intel}")
    
    cat_counts = {}
    for c in categories:
        cat_counts[c] = cat_counts.get(c, 0) + 1
    
    if cat_counts.get("coding", 0) >= 2: insights.append("Profil technique (développeur/IT)")
    if cat_counts.get("finance", 0) >= 1: insights.append("Empreinte financière détectée")
    if cat_counts.get("gaming", 0) >= 2: insights.append("Gamer actif — identité secondaire probable")
    if cat_counts.get("dating", 0) >= 1: insights.append("Présence sur plateformes de rencontre")
    if cat_counts.get("marketplace", 0) >= 1: insights.append("Activité e-commerce (eBay/Etsy/Vinted)")
    if cat_counts.get("creative", 0) >= 2: insights.append("Profil créatif (designer/artiste/musicien)")
    if cat_counts.get("professional", 0) >= 2: insights.append("Présence professionnelle forte (freelance/LinkedIn)")
    if len(results) > 15: insights.append("⚠️ EXPOSITION MASSIVE — OpSec très faible")
    
    snippet = " | ".join(insights) if insights else "Données comportementales limitées."
    md5 = hashlib.md5(query.encode()).hexdigest()
    
    return {"source": "AI-PROFILER", "category": "analysis",
            "title": f"PROFIL COMPORTEMENTAL: EXPOSITION {threat} ({score:.0f}/100)",
            "url": "", "snippet": f"{snippet} [SIG:{md5[:12]}]", "confidence": 1.0}

# ============================================================
# TASK: USERNAME PIVOT (66+ platforms)
# ============================================================
@celery_app.task(name="task_pivot_username")
def task_pivot_username(job_id: str, username: str) -> List[Dict[str, Any]]:
    async def scan():
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True,
                                     limits=httpx.Limits(max_connections=200)) as client:
            coros = [check_url(client, n, u.replace("{u}", username), c) for n, u, c in PLATFORMS]
            return await asyncio.gather(*coros, return_exceptions=True)
    loop = asyncio.new_event_loop()
    try: raw = loop.run_until_complete(scan())
    finally: loop.close()
    return [r for r in raw if isinstance(r, dict)]

# ============================================================
# TASK: EMAIL INVESTIGATION (Holehe + Name Extract + Gravatar)
# ============================================================
@celery_app.task(name="task_holehe_email")
def task_holehe_email(job_id: str, email: str) -> List[Dict[str, Any]]:
    results = []
    
    # --- 1. Extract probable name from email ---
    local = email.split("@")[0]
    clean = re.sub(r'[0-9._\-]+', ' ', local).strip().title()
    if len(clean) > 2:
        results.append({"source": "EMAIL-PARSER", "category": "analysis",
                        "title": f"Nom probable extrait: {clean}",
                        "url": "", "snippet": f"Déduction algorithmique depuis l'adresse: {local} → {clean}",
                        "confidence": 0.7})
    
    # --- 2. Gravatar check ---
    email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
    gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=404"
    try:
        r = httpx.head(gravatar_url, timeout=3.0)
        if r.status_code == 200:
            results.append({"source": "GRAVATAR", "category": "social",
                            "title": "Photo de profil Gravatar trouvée",
                            "url": f"https://www.gravatar.com/avatar/{email_hash}?s=400",
                            "snippet": "Image publique associée à cet email. Utile pour recoupement visuel.",
                            "confidence": 0.99})
    except Exception: pass

    # --- 3. Google Dork for email ---
    results.append({"source": "DORK-ENGINE", "category": "social",
                    "title": "Mentions publiques de l'email",
                    "url": f"https://www.google.com/search?q=%22{email}%22",
                    "snippet": f"Recherche de toutes les mentions indexées de {email} sur le web.",
                    "confidence": 0.85})

    # --- 4. Holehe scan ---
    try:
        from holehe.core import get_functions, import_submodules
        async def run_holehe():
            modules = import_submodules("holehe.modules")
            functions = get_functions(modules)
            out: list = []
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True,
                                         limits=httpx.Limits(max_connections=150)) as client:
                tasks = [f(email, client, out) for f in functions]
                await asyncio.gather(*tasks, return_exceptions=True)
            return out
        loop = asyncio.new_event_loop()
        try: raw = loop.run_until_complete(run_holehe())
        finally: loop.close()
        for item in raw:
            if isinstance(item, dict):
                name = item.get("name", "").lower()
                if item.get("exists") and name not in HOLEHE_BLACKLIST:
                    results.append({"source": name.upper(), "category": "social",
                                    "title": f"Compte lié: {name.capitalize()}",
                                    "url": f"https://{item.get('domain', '')}",
                                    "snippet": "Email associé confirmé via flux de récupération.",
                                    "confidence": 0.97})
    except ImportError: pass

    return results

# ============================================================
# TASK: PHONE INTELLIGENCE
# ============================================================
@celery_app.task(name="task_phone_lookup")
def task_phone_lookup(job_id: str, phone: str) -> List[Dict[str, Any]]:
    clean = re.sub(r'[^0-9+]', '', phone)
    results = [
        {"source": "GOOGLE-DORK", "category": "phone",
         "title": "Mentions web du numéro",
         "url": f"https://www.google.com/search?q=%22{clean}%22",
         "snippet": f"Recherche de toutes les mentions indexées de {clean}.",
         "confidence": 0.8},
        {"source": "PASTEBIN-DORK", "category": "phone",
         "title": "Recherche dans les Pastebins/Leaks",
         "url": f"https://www.google.com/search?q=%22{clean}%22+site:pastebin.com+OR+site:rentry.co",
         "snippet": "Scan des bases publiques de textes partagés.",
         "confidence": 0.75},
        {"source": "SOCIAL-DORK", "category": "phone",
         "title": "Corrélation réseaux sociaux",
         "url": f"https://www.google.com/search?q=%22{clean}%22+site:facebook.com+OR+site:linkedin.com+OR+site:twitter.com",
         "snippet": "Tentative de corrélation du numéro avec des profils sociaux indexés.",
         "confidence": 0.7},
        {"source": "ANNUAIRE", "category": "phone",
         "title": "Recherche annuaire inversé",
         "url": f"https://www.google.com/search?q=%22{clean}%22+annuaire+OR+pages+blanches+OR+reverse+phone",
         "snippet": "Cross-référence avec les annuaires publics inversés.",
         "confidence": 0.65},
    ]
    # Tentative de formatage pour identifier le pays
    if clean.startswith("+33"): results.append({"source": "GEO-PHONE", "category": "location",
        "title": "Pays d'origine: FRANCE 🇫🇷", "url": "",
        "snippet": f"Préfixe international +33 détecté. Opérateur mobile français probable.", "confidence": 0.99})
    elif clean.startswith("+1"): results.append({"source": "GEO-PHONE", "category": "location",
        "title": "Pays d'origine: USA/CANADA 🇺🇸", "url": "",
        "snippet": "Préfixe +1 détecté.", "confidence": 0.99})
    elif clean.startswith("+44"): results.append({"source": "GEO-PHONE", "category": "location",
        "title": "Pays d'origine: UK 🇬🇧", "url": "",
        "snippet": "Préfixe +44 détecté.", "confidence": 0.99})
    return results

# ============================================================
# TASK: IP GEOLOCATION + THREAT INTEL
# ============================================================
@celery_app.task(name="task_ip_lookup")
def task_ip_lookup(job_id: str, ip: str) -> List[Dict[str, Any]]:
    results = []
    # API 1: ip-api.com (gratuit, pas de clé)
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting"
        r = httpx.get(url, timeout=5.0)
        data = r.json()
        if data.get("status") == "success":
            flags = []
            if data.get('proxy'): flags.append("🔴 VPN/PROXY")
            if data.get('hosting'): flags.append("🟡 SERVEUR/HÉBERGEMENT")
            if data.get('mobile'): flags.append("📱 RÉSEAU MOBILE")
            flag_str = " | ".join(flags) if flags else "🟢 RÉSIDENTIEL"
            
            results.append({"source": "GEO-IP", "category": "location",
                "title": f"Localisation: {data.get('city')}, {data.get('country')}",
                "url": f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}",
                "snippet": f"ISP: {data.get('isp')} | ORG: {data.get('org')} | AS: {data.get('as')} | TZ: {data.get('timezone')} | TYPE: {flag_str}",
                "confidence": 0.99})
    except Exception: pass

    # Shodan link
    results.append({"source": "SHODAN-LINK", "category": "tech",
        "title": f"Ports ouverts & Services (Shodan)",
        "url": f"https://www.shodan.io/host/{ip}",
        "snippet": "Cliquez pour voir les services exposés (HTTP, SSH, FTP, Bases de données...) sur cette IP.",
        "confidence": 0.9})

    # Censys link
    results.append({"source": "CENSYS-LINK", "category": "tech",
        "title": f"Certificats SSL & Infrastructure (Censys)",
        "url": f"https://search.censys.io/hosts/{ip}",
        "snippet": "Analyse des certificats TLS, noms de domaine liés et services détectés.",
        "confidence": 0.9})

    # AbuseIPDB link
    results.append({"source": "ABUSEIPDB", "category": "tech",
        "title": "Historique d'abus / Signalements",
        "url": f"https://www.abuseipdb.com/check/{ip}",
        "snippet": "Vérifier si cette IP a été signalée pour du spam, hacking ou activité malveillante.",
        "confidence": 0.85})

    # VirusTotal link
    results.append({"source": "VIRUSTOTAL", "category": "tech",
        "title": "Réputation VirusTotal",
        "url": f"https://www.virustotal.com/gui/ip-address/{ip}",
        "snippet": "Analyse multi-moteur antivirus de l'adresse IP et domaines hébergés.",
        "confidence": 0.85})

    return results

# ============================================================
# TASK: EXIF FORENSICS
# ============================================================
@celery_app.task(name="task_exif_url")
def task_exif_url(job_id: str, url: str) -> List[Dict[str, Any]]:
    results = []
    try:
        import exifread
        r = httpx.get(url, timeout=10.0, follow_redirects=True)
        if r.status_code == 200:
            f = io.BytesIO(r.content)
            tags = exifread.process_file(f, details=False)
            
            # File size
            size_kb = len(r.content) / 1024
            results.append({"source": "FILE-ANALYSIS", "category": "creative",
                "title": f"Fichier téléchargé ({size_kb:.1f} KB)",
                "url": url, "snippet": f"Content-Type: {r.headers.get('content-type','N/A')} | Taille: {size_kb:.1f} KB",
                "confidence": 1.0})
            
            if not tags:
                results.append({"source": "EXIF", "category": "creative",
                    "title": "Aucune métadonnée EXIF", "url": url,
                    "snippet": "L'image a été nettoyée de ses métadonnées (stripped) ou le format ne supporte pas EXIF.",
                    "confidence": 1.0})
            else:
                important = {}
                for tag in tags:
                    if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'EXIF MakerNote'):
                        important[tag] = str(tags[tag])
                
                # Camera
                if "Image Model" in important:
                    results.append({"source": "EXIF-CAMERA", "category": "creative",
                        "title": f"Appareil: {important.get('Image Make','')} {important['Image Model']}",
                        "url": url, "snippet": f"Modèle d'appareil identifié. Logiciel: {important.get('Image Software','N/A')}",
                        "confidence": 1.0})
                
                # Date
                if "EXIF DateTimeOriginal" in important:
                    results.append({"source": "EXIF-DATE", "category": "creative",
                        "title": f"Date de prise: {important['EXIF DateTimeOriginal']}",
                        "url": url, "snippet": "Horodatage exact inscrit par le capteur au moment de la capture.",
                        "confidence": 1.0})
                
                # GPS !
                if "GPS GPSLatitude" in important:
                    results.append({"source": "EXIF-GPS 🎯", "category": "location",
                        "title": "⚠️ COORDONNÉES GPS EXTRAITES",
                        "url": url,
                        "snippet": f"Lat: {important.get('GPS GPSLatitude')} {important.get('GPS GPSLatitudeRef','')} | Lon: {important.get('GPS GPSLongitude')} {important.get('GPS GPSLongitudeRef','')}",
                        "confidence": 1.0})
                
                # All other tags
                remaining = {k:v for k,v in important.items() if 'GPS' not in k and 'Model' not in k and 'DateTime' not in k}
                if remaining:
                    summary = " | ".join([f"{k}: {v}" for k,v in list(remaining.items())[:8]])
                    results.append({"source": "EXIF-EXTRA", "category": "creative",
                        "title": f"{len(remaining)} métadonnées supplémentaires",
                        "url": url, "snippet": summary, "confidence": 0.8})
    except Exception as e:
        results.append({"source": "FORENSICS", "category": "creative",
            "title": "Erreur d'extraction", "url": url,
            "snippet": f"Impossible de traiter le fichier: {str(e)[:100]}", "confidence": 0.0})

    # Reverse image search links
    results.append({"source": "REVERSE-IMG", "category": "creative",
        "title": "Recherche inversée (Google Images)",
        "url": f"https://lens.google.com/uploadbyurl?url={url}",
        "snippet": "Trouver d'autres occurrences de cette image sur le web via Google Lens.",
        "confidence": 0.9})
    results.append({"source": "REVERSE-IMG", "category": "creative",
        "title": "Recherche inversée (TinEye)",
        "url": f"https://tineye.com/search?url={url}",
        "snippet": "TinEye indexe des milliards d'images pour retrouver la source originale.",
        "confidence": 0.9})
    results.append({"source": "REVERSE-IMG", "category": "creative",
        "title": "Recherche inversée (Yandex)",
        "url": f"https://yandex.com/images/search?rpt=imageview&url={url}",
        "snippet": "Yandex est souvent plus efficace que Google pour les visages et les paysages.",
        "confidence": 0.9})

    return results

# ============================================================
# TASK: WHOIS + DNS RECORDS
# ============================================================
@celery_app.task(name="task_whois_lookup")
def task_whois_lookup(job_id: str, domain: str) -> List[Dict[str, Any]]:
    results = []
    # WHOIS
    try:
        import whois
        w = whois.whois(domain)
        ns_raw = w.name_servers or []
        ns = ", ".join(ns_raw) if isinstance(ns_raw, list) else str(ns_raw)
        results.append({"source": "WHOIS", "category": "domain",
            "title": f"Registrar: {w.registrar}",
            "url": f"https://who.is/whois/{domain}",
            "snippet": f"Création: {w.creation_date} | Expiration: {w.expiration_date} | NS: {ns[:80]}",
            "confidence": 1.0})
        if w.emails:
            emails = w.emails if isinstance(w.emails, list) else [w.emails]
            for em in emails[:3]:
                results.append({"source": "WHOIS-EMAIL", "category": "domain",
                    "title": f"Email de contact: {em}",
                    "url": "", "snippet": "Email du registrant ou contact technique extrait du WHOIS.",
                    "confidence": 0.95})
    except Exception: pass

    # DNS Records via public API
    for record_type in ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]:
        try:
            r = httpx.get(f"https://dns.google/resolve?name={domain}&type={record_type}", timeout=4.0)
            data = r.json()
            answers = data.get("Answer", [])
            if answers:
                vals = [a.get("data", "") for a in answers[:5]]
                results.append({"source": f"DNS-{record_type}", "category": "domain",
                    "title": f"Enregistrement {record_type} ({len(answers)} trouvés)",
                    "url": "", "snippet": " | ".join(vals),
                    "confidence": 0.95})
        except Exception: pass

    # Subdomain discovery via crt.sh (Certificate Transparency)
    try:
        r = httpx.get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=8.0)
        if r.status_code == 200:
            certs = r.json()
            subdomains = set()
            for cert in certs[:100]:
                name = cert.get("name_value", "")
                for sub in name.split("\n"):
                    sub = sub.strip().lower()
                    if sub and sub != domain and "*" not in sub:
                        subdomains.add(sub)
            if subdomains:
                subdomain_list = sorted(subdomains)[:20]
                results.append({"source": "CERT-TRANSPARENCY", "category": "domain",
                    "title": f"{len(subdomains)} sous-domaines découverts",
                    "url": f"https://crt.sh/?q=%25.{domain}",
                    "snippet": " | ".join(subdomain_list[:10]) + (f" ... +{len(subdomains)-10} autres" if len(subdomains)>10 else ""),
                    "confidence": 0.95})
    except Exception: pass

    # External tools links
    results.append({"source": "SECURITY-HEADERS", "category": "domain",
        "title": "Audit des en-têtes de sécurité",
        "url": f"https://securityheaders.com/?q={domain}&followRedirects=on",
        "snippet": "Analyse automatique des headers HTTP de sécurité (CSP, HSTS, X-Frame-Options...).",
        "confidence": 0.9})
    results.append({"source": "SSL-LABS", "category": "domain",
        "title": "Analyse du certificat SSL/TLS",
        "url": f"https://www.ssllabs.com/ssltest/analyze.html?d={domain}",
        "snippet": "Score de sécurité SSL et détection de failles cryptographiques.",
        "confidence": 0.9})

    return results

# ============================================================
# ORCHESTRATOR
# ============================================================
@celery_app.task(bind=True, name="run_full_investigation")
def run_full_investigation(self, job_id: str, query: str, search_type: str) -> Dict[str, Any]:
    self.update_state(state="PROGRESS", meta={"step": "Initialisation du moteur APEX..."})
    
    results: list = []
    if search_type in ("pseudo", "name"):
        self.update_state(state="PROGRESS", meta={"step": f"Scan de {len(PLATFORMS)} plateformes..."})
        results += task_pivot_username(job_id, query)
    elif search_type == "email":
        self.update_state(state="PROGRESS", meta={"step": "Analyse email multicouche..."})
        results += task_holehe_email(job_id, query)
    elif search_type == "domain":
        self.update_state(state="PROGRESS", meta={"step": "WHOIS + DNS + Sous-domaines..."})
        results += task_whois_lookup(job_id, query)
    elif search_type == "phone":
        self.update_state(state="PROGRESS", meta={"step": "Intelligence téléphonique..."})
        results += task_phone_lookup(job_id, query)
    elif search_type == "ip":
        self.update_state(state="PROGRESS", meta={"step": "Géolocalisation + Threat Intel..."})
        results += task_ip_lookup(job_id, query)
    elif search_type == "exif":
        self.update_state(state="PROGRESS", meta={"step": "Extraction forensique EXIF..."})
        results += task_exif_url(job_id, query)

    # AI Profile
    self.update_state(state="PROGRESS", meta={"step": "Corrélation IA..."})
    valid_results = [r for r in results if isinstance(r, dict)]
    if valid_results:
        valid_results.insert(0, generate_ai_profile(valid_results, query))

    valid_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    capped = valid_results[:80]
    
    return {"job_id": job_id, "total": len(capped), "results": capped,
            "completed_at": datetime.utcnow().isoformat()}
