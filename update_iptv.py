import os
import re
import json
import hashlib
import asyncio
import aiohttp
import requests

from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

OUTPUT_FILE = "list.m3u"
OUTPUT_JSON = "channels.json"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================================================
# IPTV SOURCES
# =========================================================

SOURCES = [

    # MAIN
    "https://iptv-org.github.io/iptv/index.m3u",

    # LANGUAGES
    "https://iptv-org.github.io/iptv/languages/fas.m3u",
    "https://iptv-org.github.io/iptv/languages/kur.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u",

    # COUNTRIES
    "https://iptv-org.github.io/iptv/countries/ir.m3u",
    "https://iptv-org.github.io/iptv/countries/iq.m3u",
    "https://iptv-org.github.io/iptv/countries/tr.m3u",

    # CATEGORIES
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/entertainment.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u",

    # FREE PUBLIC PLAYLISTS
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
]

# =========================================================
# KEYWORDS
# =========================================================

KURDISH_KEYWORDS = [
    "kurd",
    "kurdistan",
    "rudaw",
    "k24",
    "nrt",
    "kurdsat",
    "speda",
    "sterk",
    "rojava",
    "badinan",
    "zagros",
]

PERSIAN_KEYWORDS = [
    "iran",
    "irib",
    "persian",
    "farsi",
    "manoto",
    "gem",
    "ifilm",
    "varzesh",
    "persiana",
    "telewebion",
]

MOVIE_KEYWORDS = [
    "movie",
    "movies",
    "film",
    "cinema",
    "series",
    "action",
    "drama",
    "vod",
    "netflix",
    "fox movies",
    "star movies",
]

ADULT_KEYWORDS = [
    "adult",
    "xxx",
    "18+",
    "playboy",
    "brazzers",
    "hustler",
    "redlight",
]

ALL_KEYWORDS = (
    KURDISH_KEYWORDS
    + PERSIAN_KEYWORDS
    + MOVIE_KEYWORDS
    + ADULT_KEYWORDS
)

# =========================================================
# DOWNLOAD
# =========================================================

def download(url):

    try:

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        r.raise_for_status()

        return r.text

    except Exception as e:

        print("DOWNLOAD ERROR:", url, e)

        return ""

# =========================================================
# PARSE M3U
# =========================================================

def parse_m3u(content):

    lines = content.splitlines()

    channels = []

    for i in range(len(lines)):

        line = lines[i].strip()

        if line.startswith("#EXTINF"):

            if i + 1 < len(lines):

                url = lines[i + 1].strip()

                if url.startswith("http"):

                    channels.append((line, url))

    return channels

# =========================================================
# FILTER
# =========================================================

def extract_blob(extinf, url):

    return f"{extinf} {url}".lower()

def is_target_channel(extinf, url):

    blob = extract_blob(extinf, url)

    return any(k in blob for k in ALL_KEYWORDS)

# =========================================================
# CATEGORY
# =========================================================

def categorize(name):

    n = name.lower()

    if any(k in n for k in ADULT_KEYWORDS):
        return "Adult"

    if any(k in n for k in MOVIE_KEYWORDS):
        return "Movies"

    if any(k in n for k in KURDISH_KEYWORDS):
        return "Kurdish"

    if any(k in n for k in PERSIAN_KEYWORDS):
        return "Persian"

    return "Other"

# =========================================================
# URL NORMALIZATION
# =========================================================

def normalize_url(url):

    return url.split("?")[0].lower().strip()

# =========================================================
# STREAM CHECK
# =========================================================

async def check_stream(session, url):

    try:

        async with session.get(
            url,
            timeout=8,
            allow_redirects=True
        ) as r:

            content_type = r.headers.get(
                "Content-Type",
                ""
            ).lower()

            if (
                r.status == 200 and
                (
                    "video" in content_type
                    or "mpegurl" in content_type
                    or ".m3u8" in url
                )
            ):

                return True

    except:
        pass

    return False

# =========================================================
# BUILD PLAYLIST
# =========================================================

async def build_playlist():

    raw_channels = []

    for source in SOURCES:

        print("SOURCE:", source)

        content = download(source)

        if not content:
            continue

        channels = parse_m3u(content)

        for extinf, url in channels:

            if is_target_channel(extinf, url):

                raw_channels.append((extinf, url))

    print("RAW:", len(raw_channels))

    deduped = {}

    for extinf, url in raw_channels:

        normalized = normalize_url(url)

        if normalized not in deduped:

            deduped[normalized] = (extinf, url)

    print("DEDUPED:", len(deduped))

    final_channels = []

    connector = aiohttp.TCPConnector(limit=100)

    async with aiohttp.ClientSession(
        headers=HEADERS,
        connector=connector
    ) as session:

        tasks = []

        entries = list(deduped.values())

        for extinf, url in entries:

            tasks.append(
                asyncio.create_task(
                    check_stream(session, url)
                )
            )

        results = await asyncio.gather(*tasks)

        for idx, ok in enumerate(results):

            if ok:

                extinf, url = entries[idx]

                name = re.sub(
                    r'#EXTINF:-1.*?,',
                    '',
                    extinf
                ).strip()

                group = categorize(name)

                if 'group-title="' in extinf:

                    extinf = re.sub(
                        r'group-title=".*?"',
                        f'group-title="{group}"',
                        extinf
                    )

                else:

                    extinf = extinf.replace(
                        "#EXTINF:-1",
                        f'#EXTINF:-1 group-title="{group}"'
                    )

                final_channels.append((extinf, url))

    final_channels.sort(
        key=lambda x: re.sub(
            r'#EXTINF:-1.*?,',
            '',
            x[0]
        ).lower()
    )

    return final_channels

# =========================================================
# SAVE PLAYLIST
# =========================================================

def write_playlist(channels):

    content = "#EXTM3U\n"

    for extinf, url in channels:

        content += f"{extinf}\n{url}\n"

    old_hash = None

    if os.path.exists(OUTPUT_FILE):

        with open(OUTPUT_FILE, "rb") as f:

            old_hash = hashlib.md5(
                f.read()
            ).hexdigest()

    new_hash = hashlib.md5(
        content.encode("utf-8")
    ).hexdigest()

    updated = old_hash != new_hash

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)

    data = []

    for extinf, url in channels:

        name = re.sub(
            r'#EXTINF:-1.*?,',
            '',
            extinf
        ).strip()

        group = categorize(name)

        data.append({
            "name": name,
            "group": group,
            "stream": url
        })

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump({
            "updated": datetime.utcnow().isoformat(),
            "total": len(data),
            "channels": data
        }, f, indent=2, ensure_ascii=False)

    return updated

# =========================================================
# TELEGRAM
# =========================================================

async def send_telegram(channels, updated):

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:

        print("TELEGRAM CONFIG MISSING")

        return

    status = "UPDATED ✅" if updated else "NO CHANGE ⚠️"

    grouped = {
        "Kurdish": [],
        "Persian": [],
        "Movies": [],
        "Adult": [],
        "Other": [],
    }

    for extinf, url in channels:

        name = re.sub(
            r'#EXTINF:-1.*?,',
            '',
            extinf
        ).strip()

        group = categorize(name)

        grouped[group].append(name)

    message = (
        f"📡 IPTV UPDATE\n\n"
        f"Status: {status}\n"
        f"Total Channels: {len(channels)}\n"
        f"UTC: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    for group, names in grouped.items():

        if not names:
            continue

        message += f"📂 {group} ({len(names)})\n"

        unique_names = sorted(set(names))

        for n in unique_names[:50]:

            message += f"• {n}\n"

        if len(unique_names) > 50:

            message += f"... +{len(unique_names)-50} more\n"

        message += "\n"

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message[:4000]
    }

    try:

        async with aiohttp.ClientSession() as session:

            async with session.post(
                url,
                data=payload,
                timeout=15
            ) as r:

                print("TELEGRAM:", r.status)

    except Exception as e:

        print("TELEGRAM ERROR:", e)

# =========================================================
# MAIN
# =========================================================

async def main():

    print("BUILDING IPTV PLAYLIST...")

    channels = await build_playlist()

    print("FINAL CHANNELS:", len(channels))

    updated = write_playlist(channels)

    await send_telegram(
        channels,
        updated
    )

    print("DONE")

# =========================================================

if __name__ == "__main__":

    asyncio.run(main())
