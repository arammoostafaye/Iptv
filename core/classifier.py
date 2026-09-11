"""
Professional Classifier
دسته بندی حرفه ای - هر کانال دقیقا در یک گروه

قانون اصلی: Language-First
مثلا iFilm فارسی است نه Movies
Rudaw کردی است نه News

گروه ها:
- Kurdish
- Persian
- Sports
- Movies
- Music
- News
- Kids
- Documentary
- Other
- DROP (حذف شود)
"""
import re
from typing import Tuple, Set, Dict

# ===== KEYWORDS =====
KURDISH_KW = [
    "kurd", "kurdi", "kurdistan", "kurmanci", "sorani", "badini",
    "rudaw", "kurdsat", "kurdmax", "zagros", "sterk", "ronahi",
    "zarok", "speda", "jiyan", "welat", "rojava", "newroz",
    "medya", "mezopotamya", "duhok", "hewler", "erbil", "sulaymaniyah",
    "amed", "kirkuk", "kerkuk", "waar", "khak", "komala", "aso tv",
    "tishk", "gali kurdistan", "cira", "med muzik", "mmc", "nrt", "k24",
    "trt kurdi", "folklor", "payam", "afarin", "rasan", "judi", "ezidxan",
    "4 kurd", "channel 8", "net tv", "ava tv", "kurdistan tv", "kurdistan24",
    "kurd channel", "gali", "waar tv", "khak tv", "kirkuk tv", "speda tv",
]

PERSIAN_KW = [
    "persian", "farsi", "parsi", "pars",
    "iran", "irib", "irinn", "jame-jam", "jam-e-jam", "varzesh", "mostanad",
    "pooya", "nahal", "tamasha", "nasim", "ofogh", "amouzesh", "salamat",
    "shoma", "tehran", "press tv", "hispan tv", "al-alam", "al-kawthar", "sahar",
    "manoto", "ifilm", "gem", "persiana", "tapesh", "pmc", "radio javan",
    "mihan", "sat7", "mohabat", "kalameh", "nejat", "hodhod", "tolo", "tolonews",
    "ariana", "shamshad", "khurshid", "lemar", "1tv", "hewad", "mitra", "zan tv",
    "tamadon", "batur", "arezo", "watan tv", "negah", "iman tv", "noorin",
    "bbc persian", "voa persian", "iran international", "simaye azadi", "andisheh",
    "omid-e-iran", "nour tv", "azadi", "marjaeyat", "ayeneh", "vivana", "shabakeh",
    "itn", "marjan", "afn", "didar", "channel one", "apadana", "navahang",
    "ava family", "ava series", "sharq tv", "dunya naw", "tv farah", "20tv",
    "xo tv", "play plus", "24box", "payam aramesh", "saamen", "oxir",
]

SPORTS_KW = [
    "sport", "sports", "varzesh", "football", "soccer", "laliga", "premier league",
    "bundesliga", "serie a", "champions league", "europa", "persiana sports",
    "varzesh tv", "football tv", "sport tv", "bein sport", "eleven sport",
]

MOVIE_KW = [
    "movie", "movies", "film", "cinema", "cine", "series", "serial", "vod",
    "drama", "fox movies", "star movies", "sony movies", "amc", "rotana cinema",
    "mbc 2", "mbc action", "mbc drama", "cairo cinema", "cairo drama", "waar cinema",
    "paramount", "mbc bollywood", "gem film", "gem drama", "gem series", "gem classic",
    "aflam", "hollywood", "bollywood", "netflix",
]

MUSIC_KW = [
    "music", "muzik", "mtv", "vh1", "radio javan", "pmc", "tapesh", "kral",
    "powerturk", "dream turk", "number one", "nrj", "trace", "clubbing tv",
    "med muzik", "folklor", "stereo", "rotana music", "mazzika", "hit music",
    "gem music", "tmb tv", "4music", "box music",
]

NEWS_KW = [
    "news", "khabar", "haber", "press", "al jazeera", "al arabiya", "al hadath",
    "bbc", "cnn", "euronews", "france 24", "dw ", "sky news", "rt ", "tolonews",
    "irinn", "cnbc", "fox news", "al ekhbariya", "cgtn", "trt world", "trt haber",
    "kurdistan 24", "rudaw", "nrt", "kurdsat news", "iran international",
]

KIDS_KW = [
    "kids", "kidz", "children", "cocuk", "cartoon", "animation", "baby", "junior",
    "nickelodeon", "nick jr", "disney", "boomerang", "cartoonito", "cartoon network",
    "duck tv", "baby tv", "babyfirst", "pooya", "nahal", "hodhod", "zarok",
    "minika", "trt cocuk", "pepule", "gem junior", "majid", "baraem", "jeem",
    "spacetoon", "mbc 3", "yaslyk", "toyor", "rotana kids", "aso kids", "anime",
    "afarin", "baxcha",
]

DOC_KW = [
    "documentary", "document", "belgesel", "mostanad", "wildlife", "nature",
    "animal planet", "national geographic", "nat geo", "discovery", "history",
    "da vinci", "planet", "explorer", "love nature", "smithsonian", "docubox",
    "trt belgesel", "tgrt belgesel", "al jazeera documentary", "travel xp",
]

ADULT_KW = [
    "adult", "xxx", "18+", "playboy", "brazzers", "hustler", "redlight",
    "penthouse", "dorcel", "vivid", "erox", "pink", "porn", "sex",
]

# DB Category Map
DB_CAT_MAP = {
    "movies": "movie", "series": "movie", "classic": "movie",
    "music": "music",
    "news": "news", "business": "news",
    "kids": "kids", "animation": "kids", "family": "kids",
    "documentary": "doc", "science": "doc", "culture": "doc", "travel": "doc",
    "sports": "sports",
}

def _mk_regex(words):
    esc = [re.escape(w) for w in sorted(words, key=len, reverse=True)]
    if not esc:
        return re.compile(r"$^")  # never matches
    return re.compile(r"(?:\b" + r"\b|\b".join(esc) + r"\b)", re.IGNORECASE)

RE_KUR = _mk_regex(KURDISH_KW)
RE_PER = _mk_regex(PERSIAN_KW)
RE_SPORT = _mk_regex(SPORTS_KW)
RE_MOV = _mk_regex(MOVIE_KW)
RE_MUS = _mk_regex(MUSIC_KW)
RE_NEWS = _mk_regex(NEWS_KW)
RE_KID = _mk_regex(KIDS_KW)
RE_DOC = _mk_regex(DOC_KW)
RE_ADULT = _mk_regex(ADULT_KW)

# Satellite roster (imported from original file logic)
def _norm(txt):
    t = txt.lower().strip()
    t = re.sub(r"[\W_]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

# Simplified satellite DB for classifier boost
SATELLITE_BOOST = {
    # Kurdish boost
    "rudaw": "kur", "kurdistan 24": "kur", "k24": "kur", "kurdsat": "kur",
    "kurdmax": "kur", "nrt": "kur", "waar": "kur", "ava": "kur", "zagros": "kur",
    # Persian boost
    "irib": "per", "manoto": "per", "gem": "per", "persiana": "per", "ifilm": "per",
    "bbc persian": "per", "iran international": "per", "varzesh": "per",
}

GROUP_ORDER = ["Kurdish", "Persian", "Sports", "Movies", "Music", "News", "Kids", "Documentary", "Other"]

def classify_channel(ch: dict, db: dict = None, language_first: bool = True) -> Tuple[str, Set[str]]:
    """
    Classify a channel
    Returns: (group, satellites_set)
    group can be: Kurdish, Persian, Sports, Movies, Music, News, Kids, Documentary, Other, DROP
    """
    name = ch.get("name", "")
    attrs = ch.get("attrs", {})
    url = ch.get("url", "")
    
    blob = f" {_norm(' '.join([name, attrs.get('group-title',''), attrs.get('tvg-name',''), url.split('/')[2] if url.startswith('http') else '']))} "

    # Adult filter
    if RE_ADULT.search(blob):
        return "DROP", set()

    scores = {"kur": 0, "per": 0, "sports": 0, "movie": 0, "music": 0, "news": 0, "kids": 0, "doc": 0}
    sats = set()

    # 1. tvg-language strong signal
    lang = attrs.get("tvg-language", "").lower()
    if lang.startswith(("kurd", "central kurd", "kurmanji", "sorani")):
        scores["kur"] += 10
    if lang.startswith(("persian", "farsi", "fas", "dari", "tajik", "prs")):
        scores["per"] += 10

    # 2. Satellite boost (simplified)
    norm_name = _norm(name)
    for sat_name, hint in SATELLITE_BOOST.items():
        if sat_name in norm_name:
            if hint == "kur":
                scores["kur"] += 6
            elif hint == "per":
                scores["per"] += 6

    # 3. tvg-id -> DB
    if db:
        tvg_id = attrs.get("tvg-id", "")
        entry = db.get(tvg_id) or db.get(tvg_id.split("@")[0])
        if entry:
            for c in entry.get("cats", set()):
                mapped = DB_CAT_MAP.get(c)
                if mapped:
                    scores[mapped] = scores.get(mapped, 0) + 4

    # 4. Keywords
    if RE_KUR.search(blob): scores["kur"] += 5
    if RE_PER.search(blob): scores["per"] += 5
    if RE_SPORT.search(blob): scores["sports"] += 4
    if RE_MOV.search(blob): scores["movie"] += 3
    if RE_MUS.search(blob): scores["music"] += 3
    if RE_NEWS.search(blob): scores["news"] += 3
    if RE_KID.search(blob): scores["kids"] += 3
    if RE_DOC.search(blob): scores["doc"] += 3

    # Decision - Language First
    if language_first:
        # اگر کردی و فارسی هر دو امتیاز دارند، کردی اولویت دارد (چون نادرتر است)
        if scores["kur"] > 0 and scores["kur"] >= scores["per"]:
            return "Kurdish", sats
        if scores["per"] > 0:
            return "Persian", sats

    # بعد ورزش
    if scores["sports"] >= 4:
        return "Sports", sats

    # بعد ژانرها
    genres = {
        "Movies": scores["movie"],
        "Music": scores["music"],
        "News": scores["news"],
        "Kids": scores["kids"],
        "Documentary": scores["doc"],
    }
    best_genre = max(genres, key=lambda g: genres[g])
    if genres[best_genre] > 0:
        # اگر Language-First خاموش است، اینجا هم چک کن
        if not language_first:
            if scores["kur"] > 0:
                return "Kurdish", sats
            if scores["per"] > 0:
                return "Persian", sats
        return best_genre, sats

    # اگر هیچ سیگنالی ندارد ولی از سورس های خاص است (مثل movies category)
    src = ch.get("source", "")
    for g, slug in [("Movies", "movies"), ("Music", "music"), ("News", "news"),
                    ("Kids", "kids"), ("Documentary", "documentary"), ("Sports", "sports")]:
        if f"/categories/{slug}" in src or f"/{slug}.m3u" in src:
            return g, sats

    return "DROP", sats

def classify_batch(channels: list, db: dict = None) -> list:
    """دسته بندی دسته ای"""
    kept = []
    stats = {g: 0 for g in GROUP_ORDER}
    stats["DROP"] = 0

    for ch in channels:
        group, sats = classify_channel(ch, db)
        stats[group] = stats.get(group, 0) + 1
        if group != "DROP":
            ch["group"] = group
            ch["satellites"] = sorted(sats)
            kept.append(ch)

    print(f"📂 Classification: {stats}")
    print(f"✅ Kept: {len(kept)}/{len(channels)}")
    return kept
