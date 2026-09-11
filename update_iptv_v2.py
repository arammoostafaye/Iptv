#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anon TV V2 - Professional Edition
by Aram Moostafaye - Upgraded 2026

Features:
- Modular architecture (sources/core)
- 35+ free sources
- Xtream premium scraper (Telegram + GitHub + Pastebin + Local file)
- Advanced HLS checker
- Logo resolver
- Multi-output: list.m3u, kurdish.m3u, persian.m3u, sports.m3u, etc
- JSON API
- Uptime scoring & smart dedupe

Usage:
  python update_iptv_v2.py
  python update_iptv_v2.py --skip-check  (for testing)
  python update_iptv_v2.py --limit 100   (test 100 only)

Env vars:
  CHECK_TIMEOUT=10
  CHECK_CONCURRENCY=150
  IPTV_LIMIT=0
  IPTV_SKIP_CHECK=0
  GITHUB_TOKEN=xxx (for GitHub scraper)
  TG_API_ID, TG_API_HASH (for Telegram scraper)
"""
import os
import re
import json
import hashlib
import asyncio
import aiohttp
import requests
from datetime import datetime
from collections import defaultdict

# Import our modules
from sources.free_sources import FREE_SOURCES, DB_URL
from sources.xtream_scraper import XtreamScraper
from core.checker import StreamChecker
from core.classifier import classify_batch, GROUP_ORDER
from core.logo_resolver import LogoResolver

# Config
OUTPUT_FILE = "list.m3u"
OUTPUT_JSON = "channels.json"
CACHE_FILE = "check_cache.json"
BRAND_LOGO = "https://raw.githubusercontent.com/arammoostafaye/Iptv/main/assets/logo.png"

CHECK_TIMEOUT = int(os.getenv("CHECK_TIMEOUT", "10"))
CONCURRENCY = int(os.getenv("CHECK_CONCURRENCY", "150"))
IPTV_LIMIT = int(os.getenv("IPTV_LIMIT", "0"))
SKIP_CHECK = os.getenv("IPTV_SKIP_CHECK", "0") == "1"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Kurdtvs (keep original logic for Kurdish portal)
KURDTVS = {
    "Kurdistan 24": "kurdistan24-tv", "Rudaw": "rudaw-tv-hd",
    "Kurdsat": "kurdsat-tv", "Kurdsat News": "kurdsat-news",
    "NRT": "nrt-tv-hd", "NRT2": "nrt2", "NRT4": "nrt-4",
    "Kurdmax Sorani": "kurdmax", "Kurdmax Kurmanci": "kurdmax-kurmanci",
    "Kurdmax Show": "kurdmax-show", "Kurdmax Show Kurmanci": "kurdmax-show-kurmanci",
    "Kurdmax Music": "kurdmax-music", "Kurdistan TV": "kurdistan-tv",
    "Zagros TV": "zagros-tv", "Gali Kurdistan": "gali-kurdistan-tv",
    "Net TV": "net-tv", "Newline HD": "newline-hd-tv", "Ava TV": "ava-tv",
    "Waar TV": "waar-tv", "Khak TV": "khak-tv", "Kirkuk TV": "kirkuk-tv",
    "Speda TV": "speda-tv", "Payam TV": "payam-tv", "Sterk TV": "sterk-tv",
    "Ronahi TV": "ronahi-tv", "Rasan TV": "rasan-tv", "Afarin TV": "afarin-tv",
    "Amozhgary TV": "amozhgary-tv", "Duhok TV": "duhok-tv",
    "UTV Hawler": "utv-hawler", "Cihan TV": "cihan-tv-hd", "KNN TV": "knn-channel",
    "Folklor TV": "folklor-tv", "TRT Kurdi": "trt-kurdi-tv",
    "Zarok TV": "zarok-tv-kurdmanci",
}
KURDTVS_BASE = "https://kurdtvs.net/"

SEED_CHANNELS = [
    {"name": "Kurdistan 24", "url": "https://d1x82nydcxndze.cloudfront.net/live/index.m3u8",
     "attrs": {"tvg-language": "Kurdish"}, "source": "seed"},
    {"name": "Rudaw TV", "url": "https://live.rudaw.net/hls/rudaw-tv/master.m3u8",
     "attrs": {"tvg-language": "Kurdish"}, "source": "seed"},
]

def _norm(txt):
    t = txt.lower().strip()
    t = re.sub(r"[\W_]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def download(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  ❌ DOWNLOAD ERROR {url[:60]}: {e}")
        return ""

def parse_m3u(content, source):
    lines = content.splitlines()
    channels = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith("#EXTINF"):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            name = line.rsplit(",", 1)[-1].strip()
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url.startswith("http"):
                    channels.append({"name": name, "attrs": attrs, "url": url, "source": source})
    return channels

def scrape_kurdtvs():
    out = []
    for name, slug in KURDTVS.items():
        try:
            html = requests.get(KURDTVS_BASE + slug, headers=HEADERS, timeout=20).text
            m = re.search(r"stream(?:Url)?s\s*=\s*(\[.*?\])\s*;", html, re.DOTALL)
            if not m:
                continue
            for s in json.loads(m.group(1)):
                u = s.get("url", "")
                if u.startswith("http") and ".m3u8" in u:
                    out.append({"name": name, "url": u, "attrs": {"tvg-language": "Kurdish"}, "source": "kurdtvs.net"})
                    break
        except Exception as e:
            print(f"  ⚠️ KURDTVS {slug}: {e}")
    print(f"  📡 KURDTVS: {len(out)} streams")
    return out

def load_db():
    db = {}
    try:
        text = download(DB_URL)
        if not text:
            return db
        import csv, io
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            cats = set((row.get("categories") or "").split(";"))
            db[row["id"]] = {"cats": cats, "country": row.get("country", "")}
        print(f"  📚 DB: {len(db)} entries")
    except Exception as e:
        print(f"  ⚠️ DB load error: {e}")
    return db

def normalize_url(url):
    return url.split("?")[0].lower().strip()

def clean_name(name):
    n = re.sub(r"\s{2,}", " ", name).strip()
    n = re.sub(r"\s*\[(geo.?blocked|not 24/7|offline)\]", "", n, flags=re.I)
    return n.strip(" -")

def dedupe_key(name):
    n = _norm(name)
    n = re.sub(r"\b(\d{3,4}p|u?hd|fhd|sd|hq|4k|hevc)\b", "", n)
    return re.sub(r"\s{2,}", " ", n).strip()

def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = datetime.utcnow().timestamp()
        # keep 48h
        return {u: v for u, (v, t) in data.items() if now - t < 48*3600}
    except:
        return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({u: (v, datetime.utcnow().timestamp()) for u, v in cache.items()}, f)
    except Exception as e:
        print(f"  ⚠️ CACHE SAVE ERROR: {e}")

async def build_playlist():
    print("=== 📡 Anon TV V2 Builder ===")
    print(f"Time: {datetime.utcnow().isoformat()} UTC")
    print(f"Timeout: {CHECK_TIMEOUT}s, Concurrency: {CONCURRENCY}, Limit: {IPTV_LIMIT or 'No limit'}")

    db = await asyncio.to_thread(load_db)
    logo_resolver = LogoResolver()
    await asyncio.to_thread(logo_resolver.load)

    # 1. Free sources
    raw = []
    print(f"\n📥 Fetching {len(FREE_SOURCES)} free sources...")
    for src in FREE_SOURCES:
        content = await asyncio.to_thread(download, src)
        if not content:
            continue
        parsed = parse_m3u(content, src)
        print(f"  ✅ {src[:60]}... -> {len(parsed)}")
        raw.extend(parsed)

    # 2. KurdTVS + Seeds
    raw.extend(await asyncio.to_thread(scrape_kurdtvs))
    raw.extend(dict(c) for c in SEED_CHANNELS)
    print(f"\n📦 RAW TOTAL: {len(raw)}")

    # 3. Premium sources (Xtream)
    premium_channels = []
    try:
        scraper = XtreamScraper()
        # Load from local files
        local_files = ["premium_sources.txt", "telegram_premium.txt", "github_premium.txt"]
        all_premium_links = set()
        for fp in local_files:
            if os.path.exists(fp):
                links = scraper.load_from_file(fp)
                all_premium_links.update(links)

        # Also try GitHub scraper if token exists
        github_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if github_token and os.getenv("ENABLE_GITHUB_SCRAPE") == "1":
            from sources.github_scraper import GitHubScraper
            gh = GitHubScraper(github_token)
            gh_links = await asyncio.to_thread(gh.scrape_all)
            all_premium_links.update(gh_links)
            print(f"  🔍 GitHub scrape: {len(gh_links)} links")

        # Validate premium accounts - AUTO, up to 100 accounts as requested
        if all_premium_links:
            # اگر 100+ لینک داریم، همه را تست کن (تا 100)
            to_validate = list(all_premium_links)[:100]
            print(f"\n💎 Premium: Found {len(all_premium_links)} total links, validating top {len(to_validate)} (target 100)...")
            valid = await scraper.validate_batch(to_validate, concurrency=40)
            print(f"  ✅ Valid premium accounts: {len(valid)}/{len(to_validate)}")

            # Fetch ALL categories from valid accounts (Movies, Documentary, Kids, Wildlife, etc)
            if valid:
                connector = aiohttp.TCPConnector(limit=60, ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    # تا 20 اکانت برتر را برای گرفتن کانال بیشتر تست کن
                    for m3u_url in valid[:20]:
                        def classifier_fn(ch):
                            from core.classifier import classify_channel
                            g, _ = classify_channel(ch, db)
                            return g
                        chans = await scraper.fetch_and_filter_premium(session, m3u_url, classifier_fn)
                        premium_channels.extend(chans)
                        # اگر 5000 کانال پریمیوم گرفتیم کافی است (جلوگیری از overload)
                        if len(premium_channels) > 8000:
                            print(f"  ⚠️ Reached 8000 premium channels limit, stopping")
                            break

            print(f"  📦 Premium channels (ALL categories - Movies, Documentary, Kids, Sports, Wildlife...): {len(premium_channels)}")
            raw.extend(premium_channels)

    except Exception as e:
        print(f"  ⚠️ Premium scrape error (non-fatal): {e}")
        import traceback; traceback.print_exc()

    print(f"\n📦 TOTAL WITH PREMIUM: {len(raw)}")

    # Dedupe by URL
    seen_urls, unique = set(), []
    for ch in raw:
        u = normalize_url(ch["url"])
        if u in seen_urls:
            continue
        seen_urls.add(u)
        ch["name"] = clean_name(ch["name"])
        if not ch["name"]:
            continue
        unique.append(ch)
    print(f"🔗 DEDUPED by URL: {len(unique)}")

    # Classify
    kept = classify_batch(unique, db)
    print(f"📂 KEPT after classification: {len(kept)}")

    # Stream check
    cache = load_cache()
    checker = StreamChecker(timeout=CHECK_TIMEOUT, concurrency=CONCURRENCY)
    
    # Handle limit for testing
    if IPTV_LIMIT > 0:
        print(f"⚠️ LIMIT MODE: Only checking first {IPTV_LIMIT} channels")
        # trust rest
        for i in range(IPTV_LIMIT, len(kept)):
            cache[kept[i]["url"]] = True

    results = await checker.check_batch(kept, cache=cache, skip_check=SKIP_CHECK)
    save_cache(cache)

    alive = [ch for i, ch in enumerate(kept) if results.get(i)]
    print(f"💚 ALIVE: {len(alive)}/{len(kept)}")

    # Logo resolve
    alive = await asyncio.to_thread(logo_resolver.resolve_batch, alive)

    # Name dedupe - keep highest quality
    def res_score(name):
        return StreamChecker.detect_resolution_score(name)

    src_prio = {"seed": 0, "kurdtvs.net": 1, "premium": 1}
    best = {}
    for ch in alive:
        k = dedupe_key(ch["name"]) or dedupe_key(ch["url"])
        if not k:
            continue
        # score: (source priority, -resolution, name length)
        cur_prio = src_prio.get(ch["source"], 2)
        cur_score = (cur_prio, -res_score(ch["name"]), len(ch["name"]))
        if k not in best or cur_score < best[k][0]:
            best[k] = (cur_score, ch)
    
    final = [v[1] for v in best.values()]
    print(f"✨ AFTER NAME-DEDUPE: {len(final)}")

    # Sort
    order = {g: n for n, g in enumerate(GROUP_ORDER)}
    final.sort(key=lambda c: (order.get(c["group"], 99), dedupe_key(c["name"])))
    return final

def make_extinf(ch):
    attrs = ch["attrs"]
    parts = ["#EXTINF:-1"]
    if attrs.get("tvg-id"):
        parts.append(f'tvg-id="{attrs["tvg-id"]}"')
    if attrs.get("tvg-name"):
        parts.append(f'tvg-name="{attrs["tvg-name"]}"')
    logo = attrs.get("tvg-logo") or BRAND_LOGO
    parts.append(f'tvg-logo="{logo}"')
    if attrs.get("tvg-language"):
        parts.append(f'tvg-language="{attrs["tvg-language"]}"')
    parts.append(f'group-title="{ch["group"]}"')
    return " ".join(parts) + "," + ch["name"]

def write_outputs(channels):
    # Group
    grouped = defaultdict(list)
    for ch in channels:
        grouped[ch["group"]].append(ch)

    def write_m3u(path, chans, header_extra=""):
        header = (
            "#EXTM3U\n"
            f"# +======================================+\n"
            f"#   Anon TV V2 — by Aram Moostafaye\n"
            f"#   {header_extra or 'Kurdish & Persian focused IPTV'}\n"
            f"#   https://github.com/arammoostafaye/Iptv\n"
            f"#   Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"#   Channels: {len(chans)}\n"
            f"# +======================================+\n"
        )
        content = header + "\n".join(f"{make_extinf(ch)}\n{ch['url']}" for ch in chans) + "\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  💾 WROTE {path} ({len(chans)} channels)")

    # Ensure output dir exists
    os.makedirs("output", exist_ok=True)

    # Full
    write_m3u(f"{OUTPUT_FILE}", channels, f"Full list - {len(channels)} channels")
    write_m3u(f"output/full.m3u", channels, f"Full list")

    # Split by group
    for group, chans in grouped.items():
        fname = f"{group.lower()}.m3u"
        write_m3u(fname, chans, f"{group} - {len(chans)} channels")
        write_m3u(f"output/{fname}", chans, f"{group}")

    # Combo: Kurdish + Persian (most popular)
    combo = grouped.get("Kurdish", []) + grouped.get("Persian", [])
    if combo:
        combo_sorted = sorted(combo, key=lambda c: (GROUP_ORDER.index(c["group"]) if c["group"] in GROUP_ORDER else 99, dedupe_key(c["name"])))
        write_m3u("kurdish-persian.m3u", combo_sorted, f"Kurdish + Persian - {len(combo_sorted)} channels")
        write_m3u("output/kurdish-persian.m3u", combo_sorted, f"Kurdish + Persian")

    # Sports combo
    if "Sports" in grouped:
        write_m3u("sports.m3u", grouped["Sports"], "Sports")
        write_m3u("output/sports.m3u", grouped["Sports"], "Sports")

    # JSON API
    data = [{
        "name": ch["name"],
        "group": ch["group"],
        "stream": ch["url"],
        "logo": ch["attrs"].get("tvg-logo") or BRAND_LOGO,
        "tvg_id": ch["attrs"].get("tvg-id", ""),
        "satellites": ch.get("satellites", []),
    } for ch in channels]

    counts = {k: len(v) for k, v in grouped.items()}

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.utcnow().isoformat(),
            "total": len(data),
            "groups": counts,
            "channels": data,
        }, f, indent=2, ensure_ascii=False)

    with open("output/channels.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.utcnow().isoformat(),
            "total": len(data),
            "groups": counts,
            "channels": data,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Groups: {counts}")

    # Hash check
    old_hash = None
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "rb") as f:
            old_hash = hashlib.md5(f.read()).hexdigest()
    # new hash already written, but we can compute
    with open(OUTPUT_FILE, "rb") as f:
        new_hash = hashlib.md5(f.read()).hexdigest()
    
    updated = old_hash != new_hash
    return updated, counts

async def send_telegram(channels, updated, counts):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("📢 TELEGRAM CONFIG MISSING - skipping")
        return

    status = "UPDATED ✅" if updated else "NO CHANGE ⚠️"
    grouped = defaultdict(list)
    for ch in channels:
        grouped[ch["group"]].append(ch["name"])

    message = (
        f"📡 Anon TV V2 UPDATE\n\n"
        f"Status: {status}\n"
        f"Total: {len(channels)}\n"
        f"UTC: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )
    for g in GROUP_ORDER:
        if g in counts:
            message += f"📂 {g}: {counts[g]}\n"

    message += f"\n🔗 Playlists:\n"
    message += f"• Full: {len(channels)} ch\n"
    message += f"• Kurdish: {counts.get('Kurdish',0)} ch\n"
    message += f"• Persian: {counts.get('Persian',0)} ch\n"
    message += f"• Kurdish+Persian: {counts.get('Kurdish',0)+counts.get('Persian',0)} ch\n"

    if len(message) > 4000:
        message = message[:4000] + "\n..."

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}) as r:
                print(f"📢 TELEGRAM: {r.status}")
    except Exception as e:
        print(f"📢 TELEGRAM ERROR: {e}")

async def main():
    channels = await build_playlist()
    updated, counts = write_outputs(channels)
    await send_telegram(channels, updated, counts)

    print("\n=== 🎯 SUMMARY ===")
    print(f"Total: {len(channels)}")
    for g in GROUP_ORDER:
        if g in counts:
            print(f"  {g}: {counts[g]}")

if __name__ == "__main__":
    asyncio.run(main())
