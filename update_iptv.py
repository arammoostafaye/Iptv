#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================
 Anon TV — IPTV Auto Builder
 by Aram Moostafaye
 https://github.com/arammoostafaye/Iptv

 Focus: Kurdish & Persian TV (Nilesat, Badr, Yahsat,
 TurkmenAlem/MonacoSat, Hotbird, Turksat)

 Categories (each channel lands in EXACTLY ONE group):
   Kurdish | Persian | Movies | Music | News | Kids | Documentary | Other

 Telegram settings are UNCHANGED (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).
=============================================================
"""

import os
import re
import csv
import io
import json
import hashlib
import asyncio
import aiohttp
import requests

from datetime import datetime

# =============================================================
# CONFIG
# =============================================================

OUTPUT_FILE = "list.m3u"
OUTPUT_JSON = "channels.json"
CACHE_FILE  = "check_cache.json"

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Brand logo (used as fallback tvg-logo for channels without one)
BRAND_LOGO = "https://raw.githubusercontent.com/arammoostafaye/Iptv/main/assets/logo.png"

# Runtime knobs (all optional)
CHECK_TIMEOUT = int(os.getenv("CHECK_TIMEOUT", "7"))       # seconds per stream probe
CONCURRENCY   = int(os.getenv("CHECK_CONCURRENCY", "120")) # parallel probes
IPTV_LIMIT    = int(os.getenv("IPTV_LIMIT", "0"))          # 0 = no limit (testing aid)
SKIP_CHECK    = os.getenv("IPTV_SKIP_CHECK", "0") == "1"   # trust all (testing aid)
INCLUDE_ADULT = False                                      # 18+ content is filtered out

# Rule: language folders win over genre folders (removes overlap).
# e.g. iFilm -> Persian (not Movies), Rudaw -> Kurdish (not News).
LANGUAGE_FIRST = True

GROUP_ORDER = ["Kurdish", "Persian", "Movies", "Music", "News",
               "Kids", "Documentary", "Other"]

# =============================================================
# SATELLITE CHANNEL DATABASE (from public frequency listings)
# hint: kurdish | persian | other
# =============================================================

SATELLITES = {
    "Nilesat 7.0W": {
        "kurdish": [
            "Rudaw", "Rudaw HD", "Kurdistan 24", "NRT", "NRT HD", "NRT2",
            "NRT3", "NRT4", "Kurdsat", "Kurdsat HD", "Kurdsat News",
            "Kurdmax", "Kurdmax Sorani", "Kurdmax Kurmanci", "Kurdmax Show",
            "Kurdmax Show Kurmanci", "Kurdmax Music", "Kurdmax Pepule",
            "Gali Kurdistan", "Zagros TV", "Khak TV", "Kirkuk TV", "Speda TV",
            "Payam TV", "Waar TV", "Waar Cinema", "Net TV", "Newline HD",
            "Afarin TV", "Rasan TV", "UTV Hawler", "Duhok TV", "Komala TV",
            "Aso TV", "Aso Kids", "Tishk TV", "Judi TV", "Newroz TV",
            "Amozhgary TV", "Cihan TV", "KNN TV", "Folklor TV", "Ezidxan TV",
            "Kanal 4", "Freedom TV", "Ava TV", "Ava Entertainment", "ZED TV",
        ],
        "persian": [
            "iFilm", "iFilm 2", "iFilm Persian", "iFilm Arabic", "MBC Persia",
            "BBC Persian", "Iran International", "Azadi TV",
        ],
        "other": [
            "MBC 1", "MBC 2", "MBC 3", "MBC 4", "MBC Action", "MBC Drama",
            "MBC Masr", "MBC Masr 2", "MBC Bollywood", "MBC Iraq",
            "Rotana Cinema", "Rotana Khalijiah", "Rotana Music",
            "Rotana Drama", "Rotana Kids", "Al Jazeera", "Al Jazeera English",
            "Al Jazeera Mubasher", "Al Jazeera Documentary", "Al Arabiya",
            "Al Arabiya Al Hadath", "BBC Arabic", "RT Arabic", "France 24 Arabic",
            "CNBC Arabia", "Spacetoon", "Majid Kids", "Baraem", "Jeem TV",
            "Toyor Al Janah", "Toyor Baby", "Cairo Drama", "Cairo Cinema",
        ],
    },
    "Badr 26.0E": {
        "kurdish": [
            "Sahar Kurdish", "Kordestan TV", "Kermanshah TV", "Ilam TV",
            "Urmia TV", "Sahand TV",
        ],
        "persian": [
            "IRIB TV1", "IRIB TV2", "IRIB TV3", "IRIB TV4", "IRIB TV5",
            "IRINN", "IRINN 2", "Varzesh TV", "Nasim TV", "Tamasha TV",
            "Mostanad TV", "Ofogh TV", "Pooya TV", "Nahal TV", "Amouzesh TV",
            "Quran TV", "Salamat TV", "Jame-Jam 1", "Jame-Jam 2", "Jame-Jam 3",
            "iFilm Persian", "iFilm Arabic", "iFilm English", "Press TV",
            "Press TV French", "Hispan TV", "Al-Alam", "Al-Kawthar",
            "Sahar TV", "Shoma TV", "Omid TV", "Namayesh TV", "Tehran TV",
        ],
        "other": [
            "Al Arabiya", "Al Hadath", "Al Ekhbariya", "MBC 1", "MBC 2",
            "MBC 3", "MBC 4", "MBC Drama", "MBC Action",
        ],
    },
    "Yahsat 52.5E": {
        "kurdish": [
            "Kurd Channel TV", "GEM Kurd", "Channel 8",
        ],
        "persian": [
            "GEM TV", "GEM Series", "GEM Film", "GEM Classic", "GEM Drama",
            "GEM Junior", "GEM River", "GEM Bollywood", "GEM Food", "GEM Life",
            "BBC Persian", "Channel One", "HodHod Farsi", "Simaye Azadi",
            "Shabakeh 7", "Ayeneh TV", "Marjaeyat TV", "Hambastegi TV",
            "Vivana TV", "Mohabat TV", "TM TV Persian", "Afghanistan International",
        ],
        "other": [],
    },
    "TurkmenAlem / MonacoSat 52.0E": {
        "kurdish": [],
        "persian": [
            "TOLO TV", "TOLOnews", "Lemar TV", "Ariana TV", "ATN", "ATN News",
            "Shamshad TV", "Khurshid TV", "1TV Afghanistan", "Hewad TV",
            "Mitra TV", "Zan TV", "Tamadon TV", "Batur TV", "Arezo TV",
            "Watan TV", "Negah TV", "Iman TV", "Noorin TV", "BBC Persian",
            "Iran International",
        ],
        "other": [
            "Altyn Asyr", "Turkmen Owazy", "Yaslyk", "Miras", "Asgabat TV",
        ],
    },
    "Hotbird 13.0E": {
        "kurdish": [
            "Kurdsat", "Kurdsat News", "Sterk TV", "Ronahi TV", "Med Muzik",
            "Medya Haber TV", "MMC", "Cira TV", "Newroz TV", "TV10",
            "Zagros TV",
        ],
        "persian": [
            "Manoto", "Iran International", "BBC Persian", "VOA Persian",
            "Pars TV", "Channel One", "Tapesh TV", "Tapesh 2", "PMC",
            "Radio Javan TV", "ITN", "Omid-e Iran", "Jaam-e-Jam International",
            "Jame-Jam TV Network", "Nour TV", "Salaam TV", "Mihan TV",
            "Nejat TV", "Kalameh TV", "SAT7 Pars", "Mohabat TV",
            "Didar Global TV", "Persiana One", "Marjan TV", "AFN TV",
            "Iran TV Network", "Andisheh TV", "IRINN", "iFilm Persian",
            "Nasim TV", "Quran TV", "Jame-Jam 1",
        ],
        "other": [
            "Al Jazeera English", "BBC News", "Euronews", "France 24",
            "DW English", "TRT World", "CGTN", "Sky News International",
            "Love Nature", "Docubox", "Fashion TV", "Trace Urban",
        ],
    },
    "Turksat 42.0E": {
        "kurdish": [
            "TRT Kurdi", "Zarok TV", "Jiyan TV",
        ],
        "persian": [],
        "other": [
            "TRT 1", "TRT 2", "TRT Haber", "TRT Spor", "TRT Cocuk",
            "TRT Muzik", "TRT Belgesel", "TRT World", "TRT Avaz", "TRT Arabi",
            "TRT Turk", "Show TV", "Show Turk", "Kanal D", "Star TV", "ATV",
            "A Haber", "CNN Turk", "NTV", "Haberturk", "24 TV", "TGRT Haber",
            "TGRT Belgesel", "Beyaz TV", "Kanal 7", "TV8", "TLC", "Teve2",
            "A Spor", "FOX Turkiye", "Dream Turk", "Number One TV",
            "Number One Turk", "PowerTurk TV", "Kral TV", "Kral Pop TV",
            "Minika GO", "Minika Cocuk", "Haber Global", "Show Max",
            "Duck TV", "TRT EBA", "TMB TV",
        ],
    },
}

# Flatten rosters -> {normalized_name: (hint, satellite)}
ROSTER = {}
ROSTER_HINT_SCORE = {"kurdish": ("kur", 6), "persian": ("per", 6)}

def _norm(txt):
    t = txt.lower().strip()
    t = re.sub(r"[\W_]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

for _sat, _groups in SATELLITES.items():
    for _hint, _names in _groups.items():
        for _n in _names:
            ROSTER.setdefault(_norm(_n), (_hint, _sat))

# Names that must NEVER match the roster (known collisions)
ROSTER_BLACKLIST = {
    "anadolu net tv",   # Turkish channel, not the Kurdish "Net TV"
    "atn bangla", "atn bangla uk", "atn news bangla",  # Bangladeshi ATN
    "azan tv",          # not Afghan "Zan TV"
}

# =============================================================
# PLAYLIST SOURCES
# =============================================================

SOURCES = [
    # MASTER (matched against satellite rosters)
    "https://iptv-org.github.io/iptv/index.m3u",
    # LANGUAGES
    "https://iptv-org.github.io/iptv/languages/fas.m3u",
    "https://iptv-org.github.io/iptv/languages/kur.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    # COUNTRIES
    "https://iptv-org.github.io/iptv/countries/ir.m3u",
    "https://iptv-org.github.io/iptv/countries/iq.m3u",
    "https://iptv-org.github.io/iptv/countries/tr.m3u",
    "https://iptv-org.github.io/iptv/countries/af.m3u",
    "https://iptv-org.github.io/iptv/countries/sy.m3u",
    # CATEGORIES
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/entertainment.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u",
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    # FREE PUBLIC PLAYLISTS
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
]

# iptv-org channel database (id -> categories/country) for tvg-id matching
DB_URL = "https://raw.githubusercontent.com/iptv-org/database/master/data/channels.csv"

# Kurdish live TV portal — stream URLs scraped per channel page
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

# Manually verified seeds for important channels not found via sources
SEED_CHANNELS = [
    {"name": "Kurdistan 24", "url": "https://d1x82nydcxndze.cloudfront.net/live/index.m3u8",
     "attrs": {"tvg-language": "Kurdish"}, "source": "seed"},
]

# =============================================================
# KEYWORDS (match on word boundaries, case-insensitive)
# =============================================================

KURDISH_KW = [
    "kurd", "kurdi", "kurdistan", "kurmanci", "sorani", "rudaw", "kurdsat",
    "kurdmax", "zagros", "sterk", "ronahi", "zarok", "speda", "jiyan",
    "welat", "rojava", "badinan", "newroz", "medya", "mezopotamya", "duhok",
    "hewler", "erbil", "sulaymaniyah", "amed", "kirkuk", "kerkuk", "nalia",
    "waar", "khak", "komala", "aso tv", "tishk", "gali kurdistan", "cira",
    "med muzik", "mmc", "nrt", "k24", "trt kurdi", "folklor",
    "payam tv", "afarin", "rasan", "judi", "ezidxan", "avroeira", "4 kurd",
]

PERSIAN_KW = [
    "persian", "farsi", "pars", "parsi", "iran", "irib", "irinn", "jame-jam",
    "jam-e-jam", "manoto", "ifilm", "varzesh", "mostanad", "pooya", "nahal",
    "tamasha", "nasim", "ofogh", "amouzesh", "salamat", "shoma", "tehran",
    "persiana", "tapesh", "pmc", "radio javan", "mihan", "sat7", "sat 7 pars",
    "mohabat", "kalameh", "nejat", "hodhod", "hod hod", "tolo", "tolonews",
    "ariana", "shamshad", "khurshid", "lemar", "1tv", "hewad", "mitra",
    "zan tv", "tamadon", "batur", "arezo", "watan tv", "negah", "iman tv",
    "noorin", "bbc persian", "voa persian", "iran international", "simaye azadi",
    "andisheh", "omid-e-iran", "nour tv", "azadi", "hambastegi", "marjaeyat",
    "ayeneh", "vivana", "shabakeh", "itn", "marjan", "afn", "didar",
    "channel one", "apadana", "gem", "press tv", "hispan tv", "al-alam",
    "al-kawthar", "sahar", "afghanistan international",
]

MOVIE_KW = [
    "movie", "movies", "film", "cinema", "cine", "series", "serial", "vod",
    "drama", "ifilm", "fox movies", "star movies", "sony movies", "amc",
    "rotana cinema", "mbc 2", "mbc action", "mbc drama", "cairo cinema",
    "cairo drama", "waar cinema", "classic movies", "paramount", "mbc bollywood",
    "gem film", "gem drama", "gem series", "gem classic", "aflam",
]

MUSIC_KW = [
    "music", "muzik", "mtv", "vh1", "radio javan", "pmc", "tapesh", "kral",
    "powerturk", "dream turk", "number one", "nrj", "trace", "clubbing tv",
    "med muzik", "jiyan", "folklor", "stereo", "rotana music", "mazzika",
    "free tv", "hit music", "gem music", "tmb tv",
]

NEWS_KW = [
    "news", "khabar", "haber", "press", "al jazeera", "aljazeera", "al arabiya",
    "al hadath", "bbc", "cnn", "euronews", "france 24", "france24", "dw ",
    "sky news", "rt ", "tolonews", "irinn", "cnbc", "abc news", "fox news",
    "al ekhbariya", "cgtn", "trt world", "trt haber", "alalam",
]

KIDS_KW = [
    "kids", "kidz", "children", "cocuk", "cartoon", "animation", "baby",
    "junior", "nickelodeon", "nick jr", "disney", "boomerang", "cartoonito",
    "cartoon network", "duck tv", "baby tv", "babyfirst", "pooya", "nahal",
    "hodhod", "zarok", "minika", "trt cocuk", "pepule", "gem junior", "majid",
    "baraem", "jeem", "spacetoon", "mbc 3", "yaslyk", "toyor", "rotana kids",
    "aso kids", "anime",
]

DOC_KW = [
    "documentary", "document", "belgesel", "mostanad", "wildlife", "wild",
    "nature", "animal planet", "national geographic", "nat geo", "discovery",
    "history", "da vinci", "planet", "explorer", "love nature", "smithsonian",
    "docubox", "trt belgesel", "tgrt belgesel", "al jazeera documentary",
    "travel xp",
]

ADULT_KW = [
    "adult", "xxx", "18+", "playboy", "brazzers", "hustler", "redlight",
    "penthouse", "dorcel", "vivid", "erox", "pink",
]

DB_CAT_MAP = {
    "movies": "movie", "series": "movie", "classic": "movie",
    "music": "music",
    "news": "news", "business": "news",
    "kids": "kids", "animation": "kids", "family": "kids",
    "documentary": "doc", "science": "doc", "culture": "doc", "travel": "doc",
}

def _mk_regex(words):
    esc = [re.escape(w) for w in sorted(words, key=len, reverse=True)]
    return re.compile(r"(?:\b" + r"\b|\b".join(esc) + r"\b)", re.IGNORECASE)

RE_KUR  = _mk_regex(KURDISH_KW)
RE_PER  = _mk_regex(PERSIAN_KW)
RE_MOV  = _mk_regex(MOVIE_KW)
RE_MUS  = _mk_regex(MUSIC_KW)
RE_NEWS = _mk_regex(NEWS_KW)
RE_KID  = _mk_regex(KIDS_KW)
RE_DOC  = _mk_regex(DOC_KW)
RE_ADULT = _mk_regex(ADULT_KW)

# =============================================================
# HELPERS
# =============================================================

def download(url, binary=False):
    try:
        r = requests.get(url, headers=HEADERS, timeout=40)
        r.raise_for_status()
        return r.content if binary else r.text
    except Exception as e:
        print("DOWNLOAD ERROR:", url, e)
        return b"" if binary else ""


def parse_m3u(content, source):
    """Return list of dicts: name, attrs, url, source"""
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
                    channels.append({
                        "name": name, "attrs": attrs,
                        "url": url, "source": source,
                    })
    return channels


def load_db():
    """iptv-org database: id -> {'cats': set, 'country': str}"""
    db = {}
    text = download(DB_URL)
    if not text:
        return db
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        cats = set((row.get("categories") or "").split(";"))
        db[row["id"]] = {"cats": cats, "country": row.get("country", "")}
    print("DB entries:", len(db))
    return db


def scrape_kurdtvs():
    """Fetch live stream URLs of Kurdish channels from kurdtvs.net"""
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
                    out.append({
                        "name": name, "url": u,
                        "attrs": {"tvg-language": "Kurdish"},
                        "source": "kurdtvs.net",
                    })
                    break
        except Exception as e:
            print("KURDTVS ERROR:", slug, e)
    print("KURDTVS streams:", len(out))
    return out


def normalize_url(url):
    return url.split("?")[0].lower().strip()


def clean_name(name):
    n = re.sub(r"\s{2,}", " ", name).strip()
    n = re.sub(r"\s*\[(geo.?blocked|not 24/7)\]", "", n, flags=re.IGNORECASE)
    return n.strip(" -")


def dedupe_key(name):
    n = _norm(name)
    n = re.sub(r"\b(\d{3,4}p|u?hd|fhd|sd|hq|4k|hevc)\b", "", n)
    return re.sub(r"\s{2,}", " ", n).strip()

# =============================================================
# CLASSIFICATION — every channel gets exactly ONE group
# =============================================================

def classify(ch, db):
    """Return (group, satellites_set). is_target decided by caller:
    channel is kept if group != 'DROP' and (matched language/genre/roster)."""
    name = ch["name"]
    attrs = ch["attrs"]
    blob = " {} ".format(_norm(" ".join([
        name, attrs.get("group-title", ""), attrs.get("tvg-name", ""),
        ch["url"].split("/")[2] if ch["url"].startswith("http") else "",
    ])))

    if not INCLUDE_ADULT and RE_ADULT.search(blob):
        return "DROP", set()

    scores = {"kur": 0, "per": 0, "movie": 0, "music": 0,
              "news": 0, "kids": 0, "doc": 0}
    sats = set()

    # 1. tvg-language (strong)
    lang = attrs.get("tvg-language", "").lower()
    if lang.startswith(("kurd", "central kurd")):
        scores["kur"] += 6
    if lang.startswith(("persian", "farsi", "dari", "tajik")):
        scores["per"] += 6

    # 2. satellite roster (strong) — exact, then safe prefix matching
    key = dedupe_key(name)
    hit = None if key in ROSTER_BLACKLIST else ROSTER.get(key)
    if hit is None and key not in ROSTER_BLACKLIST:
        for rn, (hint, sat) in ROSTER.items():
            # "Kurdsat News" starts with roster "kurdsat" ✓
            # but "Lao Net TV" must NOT match roster "net tv" ✗
            if len(rn) >= 4 and key.startswith(rn):
                hit = (hint, sat)
                break
            # "channel 8" found inside longer roster "channel 8 kurdish"
            if len(key) >= 5 and rn.startswith(key):
                hit = (hint, sat)
                break
    if hit:
        hint, sat = hit
        sats.add(sat)
        if hint in ROSTER_HINT_SCORE:
            k, v = ROSTER_HINT_SCORE[hint]
            scores[k] += v
        else:
            scores["movie"] += 1  # known but language-neutral -> keepable

    # 3. tvg-id -> iptv-org database
    tvg_id = attrs.get("tvg-id", "")
    entry = db.get(tvg_id) or db.get(tvg_id.split("@")[0])
    if entry:
        for c in entry["cats"]:
            mapped = DB_CAT_MAP.get(c)
            if mapped:
                scores[mapped] += 4

    # 4. keywords
    if RE_KUR.search(blob):  scores["kur"]   += 4
    if RE_PER.search(blob):  scores["per"]   += 4
    if RE_MOV.search(blob):  scores["movie"] += 3
    if RE_MUS.search(blob):  scores["music"] += 3
    if RE_NEWS.search(blob): scores["news"]  += 3
    if RE_KID.search(blob):  scores["kids"]  += 3
    if RE_DOC.search(blob):  scores["doc"]   += 3

    # ---- decide group (no overlap) ----
    if LANGUAGE_FIRST:
        if scores["kur"] > 0 and scores["kur"] >= scores["per"]:
            return "Kurdish", sats
        if scores["per"] > 0:
            return "Persian", sats

    genres = {"Movies": scores["movie"], "Music": scores["music"],
              "News": scores["news"], "Kids": scores["kids"],
              "Documentary": scores["doc"]}
    best = max(genres, key=lambda g: (genres[g], -GROUP_ORDER.index(g)))
    if genres[best] > 0:
        if not LANGUAGE_FIRST and scores["kur"] >= scores["per"] and scores["kur"] > 0:
            return "Kurdish", sats
        if not LANGUAGE_FIRST and scores["per"] > 0:
            return "Persian", sats
        return best, sats

    # known satellite channel but no genre signal
    if sats:
        return "Other", sats

    # themed sources give weak signal via source URL
    src = ch["source"]
    for g, slug in [("Movies", "movies"), ("Music", "music"), ("News", "news"),
                    ("Kids", "kids"), ("Documentary", "documentary")]:
        if f"/categories/{slug}" in src:
            return g, sats

    return "DROP", sats

# =============================================================
# STREAM CHECK
# =============================================================

VLC_HEADERS = {"User-Agent": "VLC/3.0.20 LibVLC/3.0.20"}
TRUSTED_SOURCES = ("kurdtvs.net",)  # portal-curated links: kept even if probe fails

async def _probe(session, sem, url, headers):
    """True = alive | False = clearly dead | None = blocked (geo/DC)"""
    try:
        async with sem:
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT),
                                   allow_redirects=True) as r:
                ct = r.headers.get("Content-Type", "").lower()
                if r.status == 200 and (
                    "video" in ct or "mpegurl" in ct or "octet-stream" in ct
                    or ".m3u8" in url
                ):
                    await r.content.read(64)  # confirm real data flows
                    return True
                if r.status in (401, 402, 403):
                    return None  # blocked for datacenter IPs, OK for end users
    except Exception:
        pass
    return False


async def check_stream(session, session_vlc, sem, url, trust=False):
    if SKIP_CHECK or trust:
        return True
    ok = await _probe(session, sem, url, HEADERS)
    if ok is True or ok is None:
        return True
    # retry with VLC fingerprint — some servers only serve players
    ok = await _probe(session_vlc, sem, url, VLC_HEADERS)
    if ok is True or ok is None:
        return True
    return False


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = datetime.utcnow().timestamp()
        return {u: v for u, (v, t) in data.items() if now - t < 48 * 3600}
    except Exception:
        return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({u: (v, datetime.utcnow().timestamp()) for u, v in cache.items()}, f)
    except Exception as e:
        print("CACHE SAVE ERROR:", e)

# =============================================================
# BUILD
# =============================================================

async def build_playlist():
    db = await asyncio.to_thread(load_db)

    raw = []
    for source in SOURCES:
        print("SOURCE:", source)
        content = await asyncio.to_thread(download, source)
        if not content:
            continue
        parsed = parse_m3u(content, source)
        print("  parsed:", len(parsed))
        raw.extend(parsed)

    raw.extend(await asyncio.to_thread(scrape_kurdtvs))
    raw.extend(dict(c) for c in SEED_CHANNELS)
    print("RAW TOTAL:", len(raw))

    # dedupe by URL only — name-dedupe happens AFTER the health check,
    # so a live stream is never dropped in favour of a dead duplicate
    seen_urls, unique = set(), []
    for ch in raw:
        u = normalize_url(ch["url"])
        if u in seen_urls:
            continue
        seen_urls.add(u)
        ch["name"] = clean_name(ch["name"])
        unique.append(ch)
    print("DEDUPED:", len(unique))

    # classify
    kept = []
    for ch in unique:
        group, sats = classify(ch, db)
        if group != "DROP":
            ch["group"] = group
            ch["satellites"] = sorted(sats)
            kept.append(ch)
    print("KEPT (target):", len(kept))

    # stream check (with cache)
    cache = load_cache()
    sem = asyncio.Semaphore(CONCURRENCY)
    conn = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=conn) as session, \
               aiohttp.ClientSession(connector=conn) as session_vlc:
        todo_idx, results = [], {}
        for i, ch in enumerate(kept):
            if ch["url"] in cache:
                results[i] = cache[ch["url"]]
            else:
                todo_idx.append(i)
        if IPTV_LIMIT > 0:
            todo_idx = todo_idx[:IPTV_LIMIT]
            for i in set(range(len(kept))) - set(results) - set(todo_idx):
                results[i] = True  # trust the rest in test mode
        if SKIP_CHECK:
            results = {i: True for i in range(len(kept))}
            todo_idx = []
        print("CHECKING:", len(todo_idx), "streams (cached:", len(results), ")")
        tasks = {
            i: asyncio.create_task(check_stream(
                session, session_vlc, sem, kept[i]["url"],
                trust=kept[i]["source"] in TRUSTED_SOURCES))
            for i in todo_idx
        }
        done = 0
        for i, t in tasks.items():
            ok = await t
            results[i] = ok
            cache[kept[i]["url"]] = ok
            done += 1
            if done % 200 == 0:
                print(f"  checked {done}/{len(tasks)}")
    save_cache(cache)

    alive = [ch for i, ch in enumerate(kept) if results.get(i)]
    print("ALIVE:", len(alive))

    # name-dedupe among alive channels, preferring curated sources & higher res
    def res_of(name):
        m = re.search(r"(\d{3,4})p", name)
        return int(m.group(1)) if m else 0

    src_prio = {"seed": 0, "kurdtvs.net": 1}
    best = {}
    for ch in alive:
        k = dedupe_key(ch["name"]) or dedupe_key(ch["url"])
        score = (src_prio.get(ch["source"], 2), -res_of(ch["name"]), len(ch["name"]))
        if k not in best or score < best[k][0]:
            best[k] = (score, ch)
    final = [v[1] for v in best.values()]
    print("AFTER NAME-DEDUPE:", len(final))

    order = {g: n for n, g in enumerate(GROUP_ORDER)}
    final.sort(key=lambda c: (order[c["group"]], dedupe_key(c["name"])))
    return final

# =============================================================
# SAVE
# =============================================================

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


def write_playlist(channels):
    header = (
        "#EXTM3U\n"
        "# +======================================+\n"
        "#   Anon TV — by Aram Moostafaye\n"
        "#   Kurdish & Persian focused IPTV list\n"
        "#   https://github.com/arammoostafaye/Iptv\n"
        "#   Updated: {ts} UTC\n"
        "# +======================================+\n"
    ).format(ts=datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    content = header + "\n".join(
        f"{make_extinf(ch)}\n{ch['url']}" for ch in channels
    ) + "\n"

    old_hash = None
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "rb") as f:
            old_hash = hashlib.md5(f.read()).hexdigest()
    new_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    updated = old_hash != new_hash

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    data = [{
        "name": ch["name"],
        "group": ch["group"],
        "stream": ch["url"],
        "logo": ch["attrs"].get("tvg-logo") or BRAND_LOGO,
        "tvg_id": ch["attrs"].get("tvg-id", ""),
        "satellites": ch["satellites"],
    } for ch in channels]

    counts = {}
    for ch in channels:
        counts[ch["group"]] = counts.get(ch["group"], 0) + 1

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.utcnow().isoformat(),
            "total": len(data),
            "groups": counts,
            "channels": data,
        }, f, indent=2, ensure_ascii=False)

    return updated

# =============================================================
# TELEGRAM  (settings unchanged)
# =============================================================

async def send_telegram(channels, updated):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM CONFIG MISSING")
        return

    status = "UPDATED ✅" if updated else "NO CHANGE ⚠️"

    grouped = {g: [] for g in GROUP_ORDER}
    sat_count = {}
    for ch in channels:
        grouped[ch["group"]].append(ch["name"])
        for s in ch["satellites"]:
            sat_count[s] = sat_count.get(s, 0) + 1

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
        for n in sorted(set(names))[:50]:
            message += f" • {n}\n"
        message += "\n"

    if sat_count:
        message += "🛰 Satellites:\n"
        for s, c in sorted(sat_count.items(), key=lambda x: -x[1]):
            message += f" • {s}: {c}\n"

    if len(message) > 4000:
        message = message[:4000] + "\n..."

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            }) as r:
                print("TELEGRAM:", r.status)
    except Exception as e:
        print("TELEGRAM ERROR:", e)

# =============================================================
# MAIN
# =============================================================

async def main():
    channels = await build_playlist()
    updated = write_playlist(channels)
    await send_telegram(channels, updated)

    print("\n=== SUMMARY ===")
    print("Total channels:", len(channels))
    counts = {}
    for ch in channels:
        counts[ch["group"]] = counts.get(ch["group"], 0) + 1
    for g in GROUP_ORDER:
        if g in counts:
            print(f"  {g}: {counts[g]}")


if __name__ == "__main__":
    asyncio.run(main())
