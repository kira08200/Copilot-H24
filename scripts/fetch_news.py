import datetime
import email.utils
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_FILE = os.path.join(BASE_DIR, "news.json")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# Positions individuelles triées par importance dans le portefeuille
STOCKS = [
    {"tv": "EURONEXT:AI", "name": "Air Liquide", "weight": "41,8 % (PEA)", "keywords": ["air liquide"]},
    {"tv": "NASDAQ:AMD", "name": "AMD", "weight": "18,4 %", "keywords": ["amd", "advanced micro devices"]},
    {"tv": "NASDAQ:NVDA", "name": "NVIDIA", "weight": "13,0 %", "keywords": ["nvidia"]},
    {"tv": "XETR:ENR", "name": "Siemens Energy", "weight": "4,8 %", "keywords": ["siemens energy"]},
    {"tv": "NYSE:BLK", "name": "BlackRock", "weight": "3,9 %", "keywords": ["blackrock"]},
    {"tv": "HKEX:1810", "name": "Xiaomi", "weight": "3,4 %", "keywords": ["xiaomi"]},
    {"tv": "NASDAQ:MSFT", "name": "Microsoft", "weight": "2,7 %", "keywords": ["microsoft"]},
    {"tv": "NASDAQ:MSTR", "name": "Strategy A", "weight": "2,0 %", "keywords": ["microstrategy", "strategy inc", "strategy a", "mstr"]},
    {"tv": "ASX:DRO", "name": "DroneShield", "weight": "0,8 %", "keywords": ["droneshield"]},
    {"tv": "NASDAQ:AAPL", "name": "Apple", "weight": "0,4 %", "keywords": ["apple"]},
    {"tv": "HKEX:1211", "name": "BYD", "weight": "0,4 %", "keywords": ["byd"]},
    {"tv": "NASDAQ:AMZN", "name": "Amazon", "weight": "0,3 %", "keywords": ["amazon"]},
    {"tv": "NASDAQ:QCOM", "name": "Qualcomm", "weight": "0,3 %", "keywords": ["qualcomm"]},
    {"tv": "NYSE:KO", "name": "Coca-Cola", "weight": "0,1 %", "keywords": ["coca-cola", "coca cola"]},
    {"tv": "NASDAQ:GOOGL", "name": "Alphabet (A)", "weight": "0,1 %", "keywords": ["alphabet", "google"]},
    {"tv": "XETR:F3C", "name": "SFC Energy", "weight": "0,03 %", "keywords": ["sfc energy"]},
]

RSS_FEEDS = [
    {
        "theme": "Cœur Portefeuille (Air Liquide / IA)",
        "tagCls": "b-purple",
        "priority": 3,
        "isGlobal": False,
        "provider": "bing",
        "url": "https://www.bing.com/news/search?q=(%22Air+Liquide%22+OR+NVIDIA+OR+AMD+OR+%22Siemens+Energy%22)+(r%C3%A9sultats+OR+chiffres+OR+trimestriel+OR+pr%C3%A9visions+OR+contrat+OR+bourse)&format=rss&mkt=fr-FR",
    },
    {
        "theme": "Big Tech & ETF (MSFT / GOOGL / BLK)",
        "tagCls": "b-blue",
        "priority": 2,
        "isGlobal": False,
        "provider": "bing",
        "url": "https://www.bing.com/news/search?q=(Microsoft+OR+Alphabet+OR+BlackRock+OR+Apple+OR+Amazon)+(r%C3%A9sultats+OR+chiffres+OR+IA+OR+bourse)&format=rss&mkt=fr-FR",
    },
    {
        "theme": "Macro, Fed, BCE & Inflation",
        "tagCls": "b-amber",
        "priority": 2,
        "isGlobal": True,
        "provider": "bing",
        "url": "https://www.bing.com/news/search?q=(Fed+OR+BCE+OR+inflation+OR+%22taux+directeurs%22+OR+%22S%26P+500%22)+(d%C3%A9cision+OR+chiffres+OR+taux+OR+march%C3%A9s)&format=rss&mkt=fr-FR",
    },
    {
        "theme": "IPO, IA & Géants Mondiaux",
        "tagCls": "b-amber",
        "priority": 2,
        "isGlobal": True,
        "provider": "bing",
        "url": "https://www.bing.com/news/search?q=(Anthropic+OR+OpenAI+OR+SpaceX+OR+IPO+OR+%22introduction+en+bourse%22+OR+TSMC+OR+ASML)+(IPO+OR+bourse+OR+valorisation+OR+milliards+OR+IA)&format=rss&mkt=fr-FR",
    },
    {
        "theme": "Asie & Spéculatif (Xiaomi / BYD / MSTR)",
        "tagCls": "b-green",
        "priority": 1,
        "isGlobal": False,
        "provider": "bing",
        "url": "https://www.bing.com/news/search?q=(Xiaomi+OR+BYD+OR+MicroStrategy+OR+DroneShield)+(r%C3%A9sultats+OR+chiffres+OR+ventes+OR+bourse)&format=rss&mkt=fr-FR",
    },
    {
        "theme": "Cœur Portefeuille (Air Liquide / IA)",
        "tagCls": "b-purple",
        "priority": 3,
        "isGlobal": False,
        "provider": "google",
        "url": "https://news.google.com/rss/search?q=(%22Air+Liquide%22+OR+NVIDIA+OR+AMD+OR+%22Siemens+Energy%22)+(r%C3%A9sultats+OR+chiffres+OR+trimestriel+OR+pr%C3%A9visions+OR+contrat+OR+earnings)&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Big Tech & ETF (MSFT / GOOGL / BLK)",
        "tagCls": "b-blue",
        "priority": 2,
        "isGlobal": False,
        "provider": "google",
        "url": "https://news.google.com/rss/search?q=(Microsoft+OR+Alphabet+OR+BlackRock+OR+Apple+OR+Amazon)+(r%C3%A9sultats+OR+chiffres+OR+IA+OR+earnings+OR+guidance)&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Macro, Fed, BCE & Inflation",
        "tagCls": "b-amber",
        "priority": 2,
        "isGlobal": True,
        "provider": "google",
        "url": "https://news.google.com/rss/search?q=(Fed+OR+BCE+OR+inflation+OR+%22taux+directeurs%22+OR+%22S%26P+500%22)+(d%C3%A9cision+OR+chiffres+OR+CPI+OR+PCE)&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "IPO, IA & Géants Mondiaux",
        "tagCls": "b-amber",
        "priority": 2,
        "isGlobal": True,
        "provider": "google",
        "url": "https://news.google.com/rss/search?q=(Anthropic+OR+OpenAI+OR+SpaceX+OR+IPO+OR+%22introduction+en+bourse%22+OR+TSMC+OR+ASML+OR+%22Wall+Street%22)+(IPO+OR+bourse+OR+valorisation+OR+milliards+OR+lev%C3%A9e+OR+krach+OR+record)&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Asie & Spéculatif (Xiaomi / BYD / MSTR)",
        "tagCls": "b-green",
        "priority": 1,
        "isGlobal": False,
        "provider": "google",
        "url": "https://news.google.com/rss/search?q=(Xiaomi+OR+BYD+OR+MicroStrategy+OR+DroneShield)+(r%C3%A9sultats+OR+chiffres+OR+ventes+OR+earnings)&hl=fr&gl=FR&ceid=FR:fr",
    },
]

ESSENTIAL_WORDS = [
    "résultat", "resultats", "résultats", "chiffre", "trimestr", "bénéfice",
    "prévision", "guidance", "dividende", "contrat", "rachat", "acquisition",
    "taux", "fed", "bce", "inflation", "cpi", "pce", "earnings", "revenue",
    "forecast", "outlook", "profit", "beat", "miss", "livraison", "ventes",
    "chute", "plonge", "dévisse", "envole", "bondit", "record", "alerte",
    "warning", "partenariat", "sanction", "droits de douane", "opa",
    "ipo", "introduction en bourse", "cotation", "levée de fonds", "valorisation",
    "milliard", "anthropic", "openai", "spacex", "tsmc", "asml", "wall street",
    "nasdaq", "s&p 500", "krach", "semi-conducteur",
]

GLOBAL_TOPICS = [
    {"name": "IPO & IA Mondiale", "tagCls": "b-purple", "keywords": ["anthropic", "openai", "spacex", "ipo", "introduction en bourse", "levée de fonds", "cotation", "databricks", "stripe"]},
    {"name": "Semi-conducteurs (TSMC / ASML)", "tagCls": "b-blue", "keywords": ["tsmc", "asml", "semi-conducteur", "semiconducteur", "fonderie"]},
    {"name": "Macro & Wall Street", "tagCls": "b-amber", "keywords": ["fed", "bce", "inflation", "taux", "cpi", "pce", "wall street", "nasdaq", "s&p 500", "krach", "droits de douane"]},
]

STOPWORDS_FR = {
    "apres", "avant", "avec", "dans", "pour", "sans", "sous", "vers", "chez",
    "entre", "cette", "leurs", "sont", "mais", "plus", "moins", "tres", "tout",
    "tous", "comme", "alors", "depuis", "contre", "selon", "avoir", "etre",
    "fait", "faire", "bourse", "bourses", "marche", "marches", "action", "actions",
    "mondiale", "mondiales", "publie", "annonce", "affiche", "termine", "cloture",
}


def clean_html(raw_text):
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_earnings_and_shocks():
    tickers = [s["tv"] for s in STOCKS]
    payload = json.dumps(
        {
            "symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": ["name", "earnings_release_next_date", "earnings_release_date", "change", "close", "currency"],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://scanner.tradingview.com/global/scan",
        data=payload,
        headers={"Content-Type": "text/plain;charset=UTF-8", "User-Agent": USER_AGENT},
        method="POST",
    )
    stock_by_tv = {s["tv"]: s for s in STOCKS}
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now_ts = int(now_dt.timestamp())
    today_key = now_dt.strftime("%Y%m%d")
    upcoming = []
    major_moves = []

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for row in data.get("data", []):
            tv = row.get("s")
            d = row.get("d") or []
            if tv not in stock_by_tv or len(d) < 6:
                continue
            info = stock_by_tv[tv]
            next_ts = d[1]
            last_ts = d[2]
            chg = d[3]
            close_px = d[4]
            ccy = d[5] or ""

            if isinstance(chg, (int, float)) and (chg <= -5.0 or chg >= 7.0):
                kind = "drop" if chg <= -5.0 else "jump"
                major_moves.append(
                    {
                        "id": f"move_{kind}_{tv}_{today_key}",
                        "tv": tv,
                        "name": info["name"],
                        "weight": info["weight"],
                        "changePct": round(chg, 2),
                        "price": close_px,
                        "currency": ccy,
                        "kind": kind,
                    }
                )

            target_ts = None
            if isinstance(next_ts, (int, float)) and next_ts > now_ts - 86400:
                target_ts = int(next_ts)
            elif isinstance(last_ts, (int, float)) and last_ts > now_ts - 86400:
                target_ts = int(last_ts)

            if target_ts:
                dt = datetime.datetime.fromtimestamp(target_ts, tz=datetime.timezone.utc)
                days_left = int((target_ts - now_ts) // 86400)
                upcoming.append(
                    {
                        "id": f"earn_{tv}_{dt.strftime('%Y%m%d')}",
                        "tv": tv,
                        "name": info["name"],
                        "weight": info["weight"],
                        "timestamp": target_ts,
                        "dateStr": dt.strftime("%d/%m/%Y"),
                        "daysLeft": max(0, days_left),
                    }
                )
        upcoming.sort(key=lambda x: x["timestamp"])
        major_moves.sort(key=lambda x: abs(x["changePct"]), reverse=True)
    except Exception as exc:
        print(f"[WARN] TradingView earnings/shocks error: {exc}")

    return upcoming[:10], major_moves[:6]


def match_stock_tag(text_lower):
    matched = []
    score = 0
    for idx, st in enumerate(STOCKS):
        if any(kw in text_lower for kw in st["keywords"]):
            matched.append(st["name"])
            score += max(1, 16 - idx)
    return matched, score


def match_global_topic(text_lower):
    for gt in GLOBAL_TOPICS:
        if any(kw in text_lower for kw in gt["keywords"]):
            return gt["name"], gt["tagCls"], 9
    return None, None, 0


def strip_source_suffix(title):
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2 and len(parts[1]) <= 32:
        return parts[0].strip()
    return title.strip()


def extract_story_tokens(title):
    core = strip_source_suffix(title).lower()
    for a, b in [("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("â", "a"), ("ô", "o"), ("û", "u"), ("ù", "u"), ("î", "i"), ("ï", "i"), ("ç", "c")]:
        core = core.replace(a, b)
    words = re.findall(r"[a-z0-9]{4,}", core)
    return {w for w in words if w not in STOPWORDS_FR}


NAMED_ENTITIES = [
    "anthropic", "openai", "spacex", "databricks", "stripe", "tsmc", "asml",
    "nvidia", "air liquide", "microsoft", "alphabet", "google", "blackrock",
    "apple", "amazon", "xiaomi", "byd", "siemens", "droneshield", "microstrategy",
    "fed", "bce",
]


def extract_named_entities(title_lower):
    found = set()
    for ent in NAMED_ENTITIES:
        if ent in title_lower:
            found.add("alphabet" if ent == "google" else ent)
    return found


def is_duplicate_story(cand, selected_list):
    c_tokens = cand.get("_tokens") or set()
    c_primary = cand.get("_primary") or ""
    c_entities = cand.get("_entities") or set()
    macro_count = sum(1 for ex in selected_list if (ex.get("_primary") or "").startswith("Macro"))
    if c_primary.startswith("Macro") and macro_count >= 2:
        return True
    for ex in selected_list:
        e_tokens = ex.get("_tokens") or set()
        e_primary = ex.get("_primary") or ""
        e_entities = ex.get("_entities") or set()
        # Maximum 1 article par entreprise / entité majeure (ex: pas 2 articles sur Anthropic ou 2 sur Nvidia ou 2 sur la Fed)
        if c_entities and e_entities and (c_entities & e_entities):
            return True
        if c_primary and e_primary and c_primary == e_primary and not c_primary.startswith("Macro"):
            return True
        if c_tokens and e_tokens:
            inter = len(c_tokens & e_tokens)
            union = len(c_tokens | e_tokens)
            smaller = min(len(c_tokens), len(e_tokens))
            if inter >= 2 and ((union > 0 and (inter / union) >= 0.30) or (smaller > 0 and (inter / smaller) >= 0.45)):
                return True
    return False


BOILERPLATE_EXCERPTS = (
    "retrouvez les dernières actualités",
    "retrouvez toute l'actualité",
    "suivez en direct",
    "toutes les informations sur",
    "cours de l'action",
    "cotation en direct",
)


def unwrap_bing_link(raw_link):
    try:
        parsed = urllib.parse.urlparse(raw_link)
        if "bing.com" in parsed.netloc:
            qs = urllib.parse.parse_qs(parsed.query)
            if qs.get("url") and qs["url"][0].startswith(("http://", "https://")):
                return qs["url"][0]
    except Exception:
        pass
    return raw_link


def extract_item_source(item, direct_link):
    source_el = item.find("source")
    if source_el is not None and source_el.text:
        return clean_html(source_el.text)
    for child in item:
        if child.tag.endswith("Source") and child.text:
            return clean_html(child.text)
    try:
        host = urllib.parse.urlparse(direct_link).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            return host.split(".")[0].capitalize()
    except Exception:
        pass
    return "Marchés"


def clean_excerpt(raw_desc, title):
    txt = clean_html(raw_desc or "")
    txt = re.sub(r"^[\*\-–—\s]+", "", txt).strip()
    if not txt or len(txt) < 35:
        return ""
    low = txt.lower()
    if any(bp in low for bp in BOILERPLATE_EXCERPTS):
        return ""
    core_title = strip_source_suffix(title).lower()
    if low.startswith(core_title[:45]) and len(txt) <= len(core_title) + 35:
        return ""
    # Nettoyer les coupures Bing du type "... les investis ..." -> dernier mot entier + "…"
    txt = re.sub(r"\s*\.\.\.\s*$", "…", txt).strip()
    if txt.endswith("…"):
        body = txt[:-1].rstrip()
        if " " in body and len(body.rsplit(" ", 1)[1]) <= 6:
            body = body.rsplit(" ", 1)[0].rstrip(" ,;:-")
        txt = body + "…"
    if len(txt) > 185:
        cut = txt[:182].rsplit(" ", 1)[0].rstrip(" ,;:-")
        txt = cut + "…"
    return txt


def fetch_excerpt_fallback(title, link):
    core = strip_source_suffix(title)
    try:
        q = urllib.parse.quote_plus(core[:95])
        url = f"https://www.bing.com/news/search?q={q}&format=rss&mkt=fr-FR"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as resp:
            root = ET.fromstring(resp.read())
        title_tokens = extract_story_tokens(core)
        for item in root.findall("./channel/item")[:5]:
            b_title = clean_html(item.findtext("title") or "")
            b_desc = clean_excerpt(item.findtext("description") or "", b_title)
            if not b_desc:
                continue
            b_tokens = extract_story_tokens(b_title)
            if title_tokens and b_tokens and len(title_tokens & b_tokens) >= 2:
                return b_desc
    except Exception:
        pass
    # Dernier recours : meta description si lien direct éditeur
    if link and "news.google.com" not in link and "bing.com" not in link:
        try:
            req = urllib.request.Request(link, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw_html = resp.read(65536).decode("utf-8", errors="ignore")
            m = re.search(
                r'<meta[^>]+(?:property=["\']og:description["\']|name=["\']description["\'])[^>]+content=["\']([^"\']{40,320})["\']',
                raw_html,
                re.IGNORECASE,
            )
            if not m:
                m = re.search(
                    r'<meta[^>]+content=["\']([^"\']{40,320})["\'][^>]+(?:property=["\']og:description["\']|name=["\']description["\'])',
                    raw_html,
                    re.IGNORECASE,
                )
            if m:
                return clean_excerpt(m.group(1), title)
        except Exception:
            pass
    return ""


def fetch_essential_news():
    candidates = []
    seen = set()
    now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    for feed in RSS_FEEDS:
        req = urllib.request.Request(feed["url"], headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)
            for item in root.findall("./channel/item")[:10]:
                title = clean_html(item.findtext("title") or "")
                raw_link = (item.findtext("link") or "").strip()
                link = unwrap_bing_link(raw_link) if feed.get("provider") == "bing" else raw_link
                pub_date = (item.findtext("pubDate") or "").strip()
                source = extract_item_source(item, link)
                raw_desc = item.findtext("description") or ""
                excerpt = clean_excerpt(raw_desc, title) if feed.get("provider") == "bing" else ""
                if not title or not link:
                    continue

                core_title = strip_source_suffix(title)
                norm = re.sub(r"[^a-z0-9]+", " ", core_title.lower()).strip()
                if norm in seen:
                    continue
                seen.add(norm)

                t_lower = title.lower()
                matched_stocks, stock_score = match_stock_tag(t_lower)
                global_theme, global_cls, global_score = match_global_topic(t_lower)
                has_essential_kw = any(w in t_lower for w in ESSENTIAL_WORDS)

                # Garder vos lignes, les IPO/géants tech mondiaux (Anthropic, OpenAI, SpaceX, TSMC...) et la macro réelle
                if not matched_stocks and not global_theme:
                    continue
                if not has_essential_kw and stock_score < 10 and global_score == 0:
                    continue

                uid = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
                pub_ts = 0
                try:
                    if pub_date:
                        pub_ts = int(email.utils.parsedate_to_datetime(pub_date).timestamp())
                except Exception:
                    pub_ts = 0

                # Ignorer les vieilles actualités (> 10 jours)
                if pub_ts > 0 and (now_ts - pub_ts) > 10 * 86400:
                    continue

                if matched_stocks and global_theme == "IPO & IA Mondiale" and any(k in t_lower for k in ("ipo", "introduction en bourse", "cotation")):
                    display_theme = matched_stocks[0] + " • IPO & IA"
                    primary_key = matched_stocks[0]
                    tag_cls = "b-purple"
                elif matched_stocks:
                    display_theme = ", ".join(matched_stocks[:2])
                    primary_key = matched_stocks[0]
                    tag_cls = feed["tagCls"]
                elif global_theme:
                    display_theme = global_theme
                    primary_key = global_theme
                    tag_cls = global_cls or feed["tagCls"]
                else:
                    display_theme = feed["theme"]
                    primary_key = feed["theme"]
                    tag_cls = feed["tagCls"]

                for special_kw in ("anthropic", "openai", "spacex", "ipo", "tsmc", "asml"):
                    if special_kw in t_lower and not matched_stocks:
                        primary_key = f"global_{special_kw}"
                        break

                age_hours = ((now_ts - pub_ts) / 3600.0) if pub_ts > 0 else 999.0
                recency_bonus = 18 if age_hours <= 24 else (8 if age_hours <= 72 else 0)
                excerpt_bonus = 4 if excerpt else 0
                relevance = feed["priority"] * 5 + stock_score + global_score + (6 if has_essential_kw else 0) + recency_bonus + excerpt_bonus
                candidates.append(
                    {
                        "id": uid,
                        "theme": display_theme,
                        "tagCls": tag_cls,
                        "title": title,
                        "excerpt": excerpt,
                        "source": source,
                        "pubDate": pub_date,
                        "pubTs": pub_ts,
                        "link": link,
                        "_score": relevance,
                        "_tokens": extract_story_tokens(title),
                        "_primary": primary_key,
                        "_entities": extract_named_entities(t_lower),
                    }
                )
        except Exception as exc:
            print(f"[WARN] RSS error ({feed['theme']}): {exc}")

    candidates.sort(key=lambda x: (x["_score"], x.get("pubTs", 0)), reverse=True)
    top_items = []
    for c in candidates:
        if len(top_items) >= 7:
            break
        if is_duplicate_story(c, top_items):
            continue
        top_items.append(c)

    for c in top_items:
        if not c.get("excerpt"):
            c["excerpt"] = fetch_excerpt_fallback(c["title"], c.get("link", ""))
        c.pop("_score", None)
        c.pop("_tokens", None)
        c.pop("_primary", None)
        c.pop("_entities", None)
    top_items.sort(key=lambda x: x.get("pubTs", 0), reverse=True)
    return top_items


def load_existing():
    if not os.path.exists(NEWS_FILE):
        return {"notifiedIds": []}
    try:
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"notifiedIds": []}


def main():
    prev = load_existing()
    notified_ids = list(prev.get("notifiedIds") or [])
    notified_set = set(notified_ids)

    upcoming_earnings, major_moves = fetch_earnings_and_shocks()
    essential_news = fetch_essential_news()

    prev_sig = (
        [(it.get("id"), it.get("excerpt") or "") for it in (prev.get("items") or [])],
        [m.get("id") for m in (prev.get("majorMoves") or [])],
        [e.get("id") for e in (prev.get("upcomingEarnings") or [])],
        list(prev.get("notifiedIds") or []),
    )

    for mv in major_moves:
        if mv["id"] not in notified_set:
            notified_ids.append(mv["id"])
            notified_set.add(mv["id"])
    for e in upcoming_earnings:
        if e["daysLeft"] <= 2 and e["id"] not in notified_set:
            notified_ids.append(e["id"])
            notified_set.add(e["id"])
    for item in essential_news:
        if item["id"] not in notified_set:
            notified_ids.append(item["id"])
            notified_set.add(item["id"])
    notified_ids = notified_ids[-150:]

    new_sig = (
        [(it.get("id"), it.get("excerpt") or "") for it in essential_news],
        [m.get("id") for m in major_moves],
        [e.get("id") for e in upcoming_earnings],
        notified_ids,
    )

    if prev.get("updatedAt") and new_sig == prev_sig:
        print("[OK] No news changes; skipping news.json update.")
        return

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "updatedAt": now_iso,
        "upcomingEarnings": upcoming_earnings,
        "majorMoves": major_moves,
        "items": essential_news,
        "notifiedIds": notified_ids,
    }

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] Saved {len(upcoming_earnings)} earnings, {len(major_moves)} major moves, {len(essential_news)} news at {now_iso}")


if __name__ == "__main__":
    main()
