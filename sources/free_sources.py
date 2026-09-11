"""
Free IPTV sources - 35+ high quality sources
Focus: Kurdish, Persian, Turkish, Arabic + Sports/Movies
"""
FREE_SOURCES = [
    # ===== IPTV-ORG OFFICIAL - MASTER =====
    "https://iptv-org.github.io/iptv/index.m3u",
    
    # ===== LANGUAGES - CORE FOCUS =====
    "https://iptv-org.github.io/iptv/languages/fas.m3u",  # Persian
    "https://iptv-org.github.io/iptv/languages/kur.m3u",  # Kurdish Kurmanji
    "https://iptv-org.github.io/iptv/languages/ckb.m3u",  # Kurdish Sorani
    "https://iptv-org.github.io/iptv/languages/ara.m3u",  # Arabic
    "https://iptv-org.github.io/iptv/languages/tuk.m3u",  # Turkmen
    "https://iptv-org.github.io/iptv/languages/tur.m3u",  # Turkish
    
    # ===== COUNTRIES - TARGET REGION =====
    "https://iptv-org.github.io/iptv/countries/ir.m3u",  # Iran
    "https://iptv-org.github.io/iptv/countries/iq.m3u",  # Iraq
    "https://iptv-org.github.io/iptv/countries/tr.m3u",  # Turkey
    "https://iptv-org.github.io/iptv/countries/af.m3u",  # Afghanistan
    "https://iptv-org.github.io/iptv/countries/sy.m3u",  # Syria
    "https://iptv-org.github.io/iptv/countries/tj.m3u",  # Tajikistan
    "https://iptv-org.github.io/iptv/countries/az.m3u",  # Azerbaijan
    "https://iptv-org.github.io/iptv/countries/tm.m3u",  # Turkmenistan
    
    # ===== CATEGORIES =====
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u",
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/entertainment.m3u",
    
    # ===== COMMUNITY REPOS - HIGH QUALITY =====
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ad.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/af.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ir.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/iq.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u",
]

# Premium sources will be loaded from file if exists
PREMIUM_SOURCES_FILE = "premium_sources.txt"
PREMIUM_SOURCES_EXAMPLE = "premium_sources.txt.example"

# IPTV-ORG Database for category mapping
DB_URL = "https://raw.githubusercontent.com/iptv-org/database/master/data/channels.csv"
LOGO_API_URL = "https://iptv-org.github.io/api/channels.json"
EPG_GUIDES_URL = "https://iptv-org.github.io/epg/guides.json"
