import datetime
import hashlib
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_FILE = os.path.join(BASE_DIR, "news.json")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

RSS_QUERIES = [
    {
        "theme": "Semi-conducteurs IA",
        "tagCls": "b-purple",
        "tickers": ["NVDA", "AMD", "QCOM"],
        "url": "https://news.google.com/rss/search?q=NVIDIA+OR+AMD+OR+Qualcomm+bourse+OR+earnings+OR+AI&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Big Tech & Cloud US",
        "tagCls": "b-blue",
        "tickers": ["MSFT", "GOOGL", "AAPL", "AMZN", "BLK"],
        "url": "https://news.google.com/rss/search?q=Microsoft+OR+Alphabet+OR+Apple+OR+Amazon+OR+BlackRock+bourse&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Industrie & Énergie EU",
        "tagCls": "b-green",
        "tickers": ["AI.PA", "ENR.DE", "F3C.DE"],
        "url": "https://news.google.com/rss/search?q=%22Air+Liquide%22+OR+%22Siemens+Energy%22+bourse+OR+r%C3%A9sultats&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Macro, Fed, BCE & Or",
        "tagCls": "b-amber",
        "tickers": ["SXR8", "XDEW", "EUNL", "PPFB"],
        "url": "https://news.google.com/rss/search?q=Fed+OR+BCE+OR+inflation+OR+%22S%26P+500%22+OR+or+march%C3%A9s&hl=fr&gl=FR&ceid=FR:fr",
    },
    {
        "theme": "Asie, VE & Spéculatif",
        "tagCls": "b-red",
        "tickers": ["1810.HK", "1211.HK", "MSTR", "DRO"],
        "url": "https://news.google.com/rss/search?q=Xiaomi+OR+BYD+OR+MicroStrategy+OR+DroneShield+action+bourse&hl=fr&gl=FR&ceid=FR:fr",
    },
]

PORTFOLIO_TV_SYMBOLS = [
    {"tv": "EURONEXT:AI", "name": "Air Liquide", "pole": "pilier"},
    {"tv": "NASDAQ:AMD", "name": "AMD", "pole": "ia"},
    {"tv": "NASDAQ:NVDA", "name": "NVIDIA", "pole": "ia"},
    {"tv": "XETR:SXR8", "name": "S&P 500 EUR", "pole": "etf"},
    {"tv": "XETR:ENR", "name": "Siemens Energy", "pole": "pilier"},
    {"tv": "NYSE:BLK", "name": "BlackRock", "pole": "etf"},
    {"tv": "HKEX:1810", "name": "Xiaomi", "pole": "tech"},
    {"tv": "NASDAQ:MSFT", "name": "Microsoft", "pole": "tech"},
    {"tv": "NASDAQ:MSTR", "name": "Strategy A", "pole": "spec"},
    {"tv": "ASX:DRO", "name": "DroneShield", "pole": "spec"},
    {"tv": "XETR:XDEW", "name": "S&P 500 Equal Weight", "pole": "etf"},
    {"tv": "XETR:PPFB", "name": "Physical Gold", "pole": "pilier"},
    {"tv": "NASDAQ:AAPL", "name": "Apple", "pole": "tech"},
    {"tv": "HKEX:1211", "name": "BYD", "pole": "tech"},
    {"tv": "NASDAQ:AMZN", "name": "Amazon", "pole": "tech"},
    {"tv": "NASDAQ:QCOM", "name": "Qualcomm", "pole": "ia"},
    {"tv": "XETR:EUNL", "name": "Core MSCI World", "pole": "etf"},
    {"tv": "NYSE:KO", "name": "Coca-Cola", "pole": "pilier"},
    {"tv": "NASDAQ:GOOGL", "name": "Alphabet (A)", "pole": "tech"},
    {"tv": "XETR:F3C", "name": "SFC Energy", "pole": "spec"},
]


def clean_html(raw_text):
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_rss_feed(cfg):
    items = []
    req = urllib.request.Request(cfg["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
        root = ET.fromstring(xml_bytes)
        for item in root.findall("./channel/item")[:5]:
            title = clean_html(item.findtext("title") or "")
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source_name = clean_html(source_el.text) if source_el is not None and source_el.text else "Actualité Marché"
            desc = clean_html(item.findtext("description") or "")
            if not title or not link:
                continue
            uid = hashlib.sha256((title.lower() + "|" + cfg["theme"]).encode("utf-8")).hexdigest()[:16]
            items.append(
                {
                    "id": uid,
                    "theme": cfg["theme"],
                    "tagCls": cfg["tagCls"],
                    "tickers": cfg["tickers"],
                    "title": title,
                    "source": source_name,
                    "pubDate": pub_date,
                    "summary": desc[:260] if desc and desc != title else "",
                    "link": link,
                }
            )
    except Exception as exc:
        print(f"[WARN] RSS error ({cfg['theme']}): {exc}")
    return items


def fetch_tv_deep_metrics():
    tickers = [x["tv"] for x in PORTFOLIO_TV_SYMBOLS]
    payload = json.dumps(
        {
            "symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": [
                "name",
                "close",
                "RSI",
                "Recommend.All",
                "price_earnings_ttm",
                "Perf.W",
                "Perf.1M",
                "Perf.3M",
                "Perf.YTD",
                "SMA50",
                "SMA200",
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://scanner.tradingview.com/global/scan",
        data=payload,
        headers={"Content-Type": "text/plain;charset=UTF-8", "User-Agent": USER_AGENT},
        method="POST",
    )
    meta_by_tv = {x["tv"]: x for x in PORTFOLIO_TV_SYMBOLS}
    results = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for row in data.get("data", []):
            tv = row.get("s")
            d = row.get("d") or []
            if tv not in meta_by_tv or len(d) < 11:
                continue
            info = meta_by_tv[tv]
            results.append(
                {
                    "tv": tv,
                    "name": info["name"],
                    "pole": info["pole"],
                    "close": d[1],
                    "rsi": d[2],
                    "recAll": d[3],
                    "pe": d[4],
                    "perfW": d[5],
                    "perf1M": d[6],
                    "perf3M": d[7],
                    "perfYTD": d[8],
                    "sma50": d[9],
                    "sma200": d[10],
                }
            )
    except Exception as exc:
        print(f"[WARN] TradingView metrics error: {exc}")
    return results


def build_deep_analysis(metrics, news_items):
    oversold = []
    overbought = []
    below_sma200 = []
    strong_buy = []
    perf_list = []

    for m in metrics:
        rsi = m.get("rsi")
        close = m.get("close")
        sma200 = m.get("sma200")
        rec = m.get("recAll")
        p1m = m.get("perf1M")
        if isinstance(rsi, (int, float)):
            if rsi < 38:
                oversold.append(f"{m['name']} (RSI {rsi:.0f})")
            elif rsi > 68:
                overbought.append(f"{m['name']} (RSI {rsi:.0f})")
        if isinstance(close, (int, float)) and isinstance(sma200, (int, float)) and sma200 > 0 and close < sma200:
            below_sma200.append(m["name"])
        if isinstance(rec, (int, float)) and rec >= 0.35:
            strong_buy.append(m["name"])
        if isinstance(p1m, (int, float)):
            perf_list.append((p1m, m["name"]))

    perf_list.sort(key=lambda x: x[0])
    laggards = [f"{n} ({v:+.1f}%)" for v, n in perf_list[:3]]
    leaders = [f"{n} ({v:+.1f}%)" for v, n in reversed(perf_list[-3:])]

    sections = []
    if leaders:
        sections.append("Leaders 1 mois : " + ", ".join(leaders) + ".")
    if laggards:
        sections.append("Lignes en repli 1 mois : " + ", ".join(laggards) + ".")
    if oversold:
        sections.append("Zone de survente technique (RSI < 38) : " + ", ".join(oversold) + ".")
    if overbought:
        sections.append("Zone tendue (RSI > 68, éviter de surcharger) : " + ", ".join(overbought) + ".")
    if below_sma200:
        sections.append("Sous moyenne mobile 200j (tendance de fond fragile) : " + ", ".join(below_sma200) + ".")
    if strong_buy:
        sections.append("Momentum haussier validé (signal technique fort) : " + ", ".join(strong_buy) + ".")

    ai_brief = maybe_generate_gemini_brief(metrics, news_items)

    return {
        "highlights": sections,
        "aiBrief": ai_brief,
        "oversoldCount": len(oversold),
        "belowSma200Count": len(below_sma200),
    }


def maybe_generate_gemini_brief(metrics, news_items):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or not news_items:
        return ""
    headlines = "\n".join([f"- [{n['theme']}] {n['title']} ({n['source']})" for n in news_items[:12]])
    tech_lines = "\n".join(
        [
            f"- {m['name']}: RSI={m['rsi']:.1f} | 1M={m['perf1M']:+.1f}% | PE={m['pe']}"
            for m in metrics
            if isinstance(m.get("rsi"), (int, float)) and isinstance(m.get("perf1M"), (int, float))
        ][:15]
    )
    prompt = (
        "Tu es analyste financier senior. Rédige une synthèse profonde et factuelle en français (max 120 mots, 3 puces claires) "
        "pour un portefeuille investi sur Air Liquide, AMD, NVIDIA, Microsoft, Alphabet, S&P 500, Siemens Energy, BlackRock, Xiaomi et BYD.\n"
        f"Actualités du jour:\n{headlines}\n\nMétriques techniques:\n{tech_lines}\n"
        "Concentre-toi sur les risques macro, catalyseurs sectoriels et points de vigilance long terme sans inventer de chiffres."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key)}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return out["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:
        print(f"[WARN] Gemini synthesis skipped: {exc}")
        return ""


def send_ntfy_alert(topic, title, message, click_url=""):
    url = f"https://ntfy.sh/{urllib.parse.quote(topic)}"
    headers = {
        "Title": title.encode("utf-8"),
        "Priority": "default",
        "Tags": "newspaper,chart_with_upwards_trend",
    }
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
        return {"notifiedIds": [], "items": []}
    try:
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"notifiedIds": [], "items": []}


def main():
    prev = load_existing()
    notified_ids = list(prev.get("notifiedIds") or [])
    notified_set = set(notified_ids)

    all_items = []
    seen_ids = set()
    for cfg in RSS_QUERIES:
        for item in fetch_rss_feed(cfg):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                all_items.append(item)

    metrics = fetch_tv_deep_metrics()
    deep_analysis = build_deep_analysis(metrics, all_items)

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_items = [it for it in all_items if it["id"] not in notified_set]

    ntfy_topic = os.environ.get("NTFY_TOPIC", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    # Envoyer au maximum 3 nouvelles alertes d'actualités par exécution (jamais sur les variations de cours)
    if new_items:
        for item in new_items[:3]:
            push_title = f"[{item['theme']}] {item['source']}"
            push_body = item["title"]
            if ntfy_topic:
                try:
                    send_ntfy_alert(ntfy_topic, push_title, push_body, item["link"])
                    print(f"[INFO] ntfy sent: {item['title']}")
                except Exception as exc:
                    print(f"[WARN] ntfy failed: {exc}")
            if tg_token and tg_chat:
                try:
                    send_telegram_alert(tg_token, tg_chat, f"📰 {push_title}\n{push_body}\n{item['link']}")
                    print(f"[INFO] Telegram sent: {item['title']}")
                except Exception as exc:
                    print(f"[WARN] Telegram failed: {exc}")

        for item in new_items:
            notified_ids.append(item["id"])
        notified_ids = notified_ids[-150:]

    output = {
        "updatedAt": now_iso,
        "count": len(all_items),
        "deepAnalysis": deep_analysis,
        "items": all_items[:20],
        "notifiedIds": notified_ids,
    }

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] Saved {len(all_items)} news items ({len(new_items)} new) at {now_iso}")


if __name__ == "__main__":
    main()
