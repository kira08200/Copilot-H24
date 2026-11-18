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
    {"tv": "NASDAQ:MSTR", "name": "Strategy A", "weight": "2,0 %", "keywords": ["microstrategy", "strategy"]},
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
        "url": "https://news.google.com/rss/search?q=(%22Air+Liquide%22+OR+NVIDIA+OR+AMD+OR+%22Siemens+Energy%22)+(r%C3%A9sultats+OR+chiffres+OR+trimestriel+OR+pr%C3%A9visions+OR+contrat+OR+earnings)&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Big Tech & ETF (MSFT / GOOGL / BLK)",
        "tagCls": "b-blue",
        "priority": 2,
        "url": "https://news.google.com/rss/search?q=(Microsoft+OR+Alphabet+OR+BlackRock+OR+Apple+OR+Amazon)+(r%C3%A9sultats+OR+chiffres+OR+IA+OR+earnings+OR+guidance)&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Macro, Fed, BCE & Inflation",
        "tagCls": "b-amber",
        "priority": 2,
        "url": "https://news.google.com/rss/search?q=(Fed+OR+BCE+OR+inflation+OR+%22taux+directeurs%22+OR+%22S%26P+500%22)+(d%C3%A9cision+OR+chiffres+OR+CPI+OR+PCE)&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Asie & Spéculatif (Xiaomi / BYD / MSTR)",
        "tagCls": "b-green",
        "priority": 1,
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
]


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


def fetch_essential_news():
    candidates = []
    seen = set()

    for feed in RSS_FEEDS:
        req = urllib.request.Request(feed["url"], headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)
            for item in root.findall("./channel/item")[:8]:
                title = clean_html(item.findtext("title") or "")
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                source_el = item.find("source")
                source = clean_html(source_el.text) if source_el is not None and source_el.text else "Marchés"
                if not title or not link:
                    continue

                norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
                if norm in seen:
                    continue
                seen.add(norm)

                t_lower = title.lower()
                matched_stocks, stock_score = match_stock_tag(t_lower)
                has_essential_kw = any(w in t_lower for w in ESSENTIAL_WORDS)

                # Ne garder que ce qui touche directement vos lignes ou la macro essentielle
                if not matched_stocks and feed["theme"] != "Macro, Fed, BCE & Inflation":
                    continue
                if not has_essential_kw and stock_score < 10:
                    continue

                uid = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
                pub_ts = 0
                try:
                    if pub_date:
                        pub_ts = int(email.utils.parsedate_to_datetime(pub_date).timestamp())
                except Exception:
                    pub_ts = 0

                relevance = feed["priority"] * 5 + stock_score + (6 if has_essential_kw else 0)
                candidates.append(
                    {
                        "id": uid,
                        "theme": ", ".join(matched_stocks[:2]) if matched_stocks else feed["theme"],
                        "tagCls": feed["tagCls"],
                        "title": title,
                        "source": source,
                        "pubDate": pub_date,
                        "pubTs": pub_ts,
                        "link": link,
                        "_score": relevance,
                    }
                )
        except Exception as exc:
            print(f"[WARN] RSS error ({feed['theme']}): {exc}")

    candidates.sort(key=lambda x: (x["_score"], x.get("pubTs", 0)), reverse=True)
    top_items = []
    for c in candidates[:6]:
        c.pop("_score", None)
        top_items.append(c)
    top_items.sort(key=lambda x: x.get("pubTs", 0), reverse=True)
    return top_items


def maybe_generate_gemini_brief(earnings, news_items):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or (not earnings and not news_items):
        return ""
    earn_txt = "\n".join([f"- {e['name']} ({e['weight']}): publication le {e['dateStr']} (dans {e['daysLeft']}j)" for e in earnings[:6]])
    news_txt = "\n".join([f"- [{n['theme']}] {n['title']} ({n['source']})" for n in news_items[:6]])
    prompt = (
        "Résume en français (maximum 3 puces très concises, sans jargon technique comme RSI ou moyennes mobiles) "
        "uniquement l'essentiel des prochains chiffres attendus et actualités clés pour ce portefeuille :\n"
        f"Prochains résultats:\n{earn_txt}\n\nActualités essentielles:\n{news_txt}"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key)}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return out["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:
        print(f"[WARN] Gemini brief skipped: {exc}")
        return ""


def send_ntfy_alert(topic, title, message, click_url=""):
    url = f"https://ntfy.sh/{urllib.parse.quote(topic)}"
    headers = {"Title": title.encode("utf-8"), "Priority": "default", "Tags": "newspaper"}
    if click_url:
        headers["Click"] = click_url
    req = urllib.request.Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def send_telegram_alert(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": False}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


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
        [it.get("id") for it in (prev.get("items") or [])],
        [m.get("id") for m in (prev.get("majorMoves") or [])],
        [e.get("id") for e in (prev.get("upcomingEarnings") or [])],
        list(prev.get("notifiedIds") or []),
    )

    ntfy_topic = os.environ.get("NTFY_TOPIC", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    alerts_to_send = []

    # 1. Alerte si grosse chute (<= -5%) ou forte envolée (>= +7%) sur une ligne
    for mv in major_moves:
        if mv["id"] not in notified_set:
            icon = "📉 Grosse chute" if mv["kind"] == "drop" else "🚀 Forte hausse"
            alerts_to_send.append(
                {
                    "id": mv["id"],
                    "title": f"{icon} : {mv['name']} ({mv['changePct']:+.1f} %)",
                    "body": f"Mouvement fort sur votre ligne ({mv['weight']}). Cours actuel : {mv['price']} {mv['currency']}.",
                    "link": "",
                }
            )

    # 2. Alerte si une de vos lignes publie ses chiffres dans les prochaines 48h
    for e in upcoming_earnings:
        if e["daysLeft"] <= 2 and e["id"] not in notified_set:
            alerts_to_send.append(
                {
                    "id": e["id"],
                    "title": f"Chiffres à venir : {e['name']}",
                    "body": f"Publication des résultats prévue le {e['dateStr']} ({e['weight']} du portefeuille).",
                    "link": "",
                }
            )

    # 3. Alerte sur les nouvelles actualités essentielles liées à vos lignes (max 2 par cycle)
    for item in essential_news:
        if item["id"] not in notified_set:
            alerts_to_send.append(
                {
                    "id": item["id"],
                    "title": f"[{item['theme']}] {item['source']}",
                    "body": item["title"],
                    "link": item["link"],
                }
            )

    for al in alerts_to_send[:2]:
        if ntfy_topic:
            try:
                send_ntfy_alert(ntfy_topic, al["title"], al["body"], al["link"])
                print(f"[INFO] ntfy sent: {al['title']}")
            except Exception as exc:
                print(f"[WARN] ntfy failed: {exc}")
        if tg_token and tg_chat:
            try:
                txt = f"📰 {al['title']}\n{al['body']}" + (f"\n{al['link']}" if al["link"] else "")
                send_telegram_alert(tg_token, tg_chat, txt)
                print(f"[INFO] Telegram sent: {al['title']}")
            except Exception as exc:
                print(f"[WARN] Telegram failed: {exc}")

    for al in alerts_to_send:
        notified_ids.append(al["id"])
    notified_ids = notified_ids[-150:]

    new_sig = (
        [it.get("id") for it in essential_news],
        [m.get("id") for m in major_moves],
        [e.get("id") for e in upcoming_earnings],
        notified_ids,
    )

    if prev.get("updatedAt") and new_sig == prev_sig:
        print("[OK] No news changes; skipping news.json update.")
        return

    ai_brief = maybe_generate_gemini_brief(upcoming_earnings, essential_news) if (not prev.get("updatedAt") or new_sig[:3] != prev_sig[:3]) else (prev.get("aiBrief") or "")

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "updatedAt": now_iso,
        "upcomingEarnings": upcoming_earnings,
        "majorMoves": major_moves,
        "aiBrief": ai_brief,
        "items": essential_news,
        "notifiedIds": notified_ids,
    }

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] Saved {len(upcoming_earnings)} earnings, {len(major_moves)} major moves, {len(essential_news)} news at {now_iso}")


if __name__ == "__main__":
    main()
