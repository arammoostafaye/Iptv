# 📡 Anon TV — IPTV V2 Professional

![auto update](assets/badge-update.svg)
![focus](assets/badge-focus.svg)
![verified](assets/badge-verified.svg)

**Auto-updated IPTV playlist focused on Kurdish and Persian TV — Now with Premium Support & Web Player**

by **Aram Moostafaye** • [github.com/arammoostafaye/Iptv](https://github.com/arammoostafaye/Iptv)

> 🚀 **V2 NEW:** 35+ sources, Xtream premium scraper, multi-output, web player, logo resolver, advanced checker

---

### 🎬 Web Player — تماشای آنلاین

**[▶️ Watch Now on GitHub Pages](https://arammoostafaye.github.io/Iptv/)** — پلیر تحت وب با جستجو و فیلتر

---

### ▶️ Playlists — استفاده در VLC / TiviMate / Kodi

#### Full & Combo (پیشنهادی)
```m3u
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/list.m3u
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/kurdish-persian.m3u
```

#### Split by Language (سبک و سریع)
```m3u
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/kurdish.m3u      # فقط کردی - 100% Kurdish
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/persian.m3u      # فقط فارسی
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/sports.m3u       # ورزشی
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/movies.m3u
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/news.m3u
```

#### JSON API برای اپلیکیشن ها
```json
https://raw.githubusercontent.com/arammoostafaye/Iptv/main/channels.json
```

**نصب در TiviMate / VLC:** آدرس بالا را به‌عنوان Playlist URL وارد کنید. لیست هر **6 ساعت** به‌صورت خودکار بررسی و به‌روز می‌شود.

---

### 📂 دسته‌بندی‌ها (هر کانال فقط در یک گروه - بدون تداخل)

| Group | توضیح | فایل |
|-------|-------|------|
| 🟥 Kurdish | روداو، کوردستان٢٤، کوردسات، کوردماکس، NRT، زاگرۆس، Waar، Ava... | `kurdish.m3u` |
| 🟩 Persian | IRIB، آی‌فیلم، GEM، منوتو، BBC Persian، Persiana، Varzesh... | `persian.m3u` |
| ⚽ Sports | Persiana Sports، Varzesh TV، Football، BeIN... | `sports.m3u` |
| 🎬 Movies | فیلم و سریال | `movies.m3u` |
| 🎵 Music | موزیک - Radio Javan، PMC، Tapesh... | `music.m3u` |
| 📰 News | اخبار | `news.m3u` |
| 🧸 Kids | کارتون و کودک - Zarok، Baxcha... | `kids.m3u` |
| 🐆 Documentary | مستند و حیات‌وحش | `documentary.m3u` |

> **قانون ضدتداخل:** Language-first — مثلاً iFilm فارسی است نه Movies؛ Rudaw کردی است نه News.

---

### 🛰 منابع ماهواره

کانال‌ها بر اساس فرهنگ فرکانسی این ماهواره‌ها تطبیق داده می‌شوند:
**Nilesat 7°W • Badr 26°E • Yahsat 52.5°E • TurkmenAlem/MonacoSat 52°E • Hotbird 13°E • Türksat 42°E**

#### منابع جدید V2 (35+ سورس):
- ✅ `iptv-org` کامل (8 کشور + 7 دسته)
- ✅ Free-TV, Tundracr3ator, Paradise IPTV
- ✅ Kurdish specialized repos
- ✅ Persian specialized repos
- ✅ **Premium Xtream accounts** (اختیاری - لو رفته از تلگرام/گیتهاب)
- ✅ kurdtvs.net scraper

---

### 💎 بخش پریمیوم — چطور اکانت اشتراکی اضافه کنیم؟

این بخش مهمترین ارتقای V2 است. 90% کانال‌های Full HD فارسی/کردی از اکانت‌های Xtream لو رفته می‌آید.

#### چطور کار میکند؟
اکانت Xtream معمولا این شکلی لو میره:
```
http://server.com:8080/get.php?username=USER&password=PASS&type=m3u_plus
```

#### از کجا پیدا کنیم؟
1. **تلگرام (بهترین):** کانال‌های `@IPTV_M3U_WORLD`, `@xtream_iptv_free`, `@freeiptv2026`
2. **سایت iptvcat.com** - هر 10 دقیقه آپدیت
3. **GitHub search:** `get.php?username= password type=m3u_plus`
4. **Reddit:** r/IPTV

#### چطور اضافه کنیم؟ (امن)

**روش 1: فایل لوکال (پیشنهادی)**
```bash
# یک فایل بساز (این فایل در .gitignore است و کامیت نمیشود)
echo "http://server:8080/get.php?username=xxx&password=yyy&type=m3u_plus" > premium_sources.txt
python update_iptv_v2.py
```

**روش 2: GitHub Secrets (برای Actions)**
1. به Settings → Secrets → Actions برو
2. یک Secret به نام `PREMIUM_SOURCES` بساز
3. تمام لینک‌های M3U را آنجا بگذار (هر خط یکی)
4. Actions به صورت خودکار آن را میخواند

**روش 3: اتومات با Telegram Scraper**
```bash
pip install telethon
# TG_API_ID و TG_API_HASH را از my.telegram.org بگیر
python -m sources.telegram_scraper --channels IPTV_M3U_WORLD xtream_iptv_free --limit 300
```

**امنیت:**
- هرگز یوزر/پسورد خام را در گیتهاب پابلیک کامیت نکن
- فقط استریم‌های فیلتر شده کردی/فارسی در خروجی می‌آید، نه اکانت خام
- اکانت‌ها هر 24 ساعت میمیرند - اسکریپت هر 6 ساعت چک میکند

---

### ⚙️ راه‌اندازی روی ریپوی خود

#### روش سریع:
1. Fork کن
2. در Settings → Secrets اضافه کن:
   - `TELEGRAM_TOKEN` و `TELEGRAM_CHAT_ID` (اختیاری - گزارش تلگرام)
   - `PREMIUM_SOURCES` (اختیاری - اکانت‌های پریمیوم)
   - `GH_TOKEN` (اختیاری - برای GitHub scraper)
3. GitHub Actions → **IPTV Auto Update V2** → Run
4. GitHub Pages را فعال کن: Settings → Pages → Source: `gh-pages` branch → برای وب پلیر

#### لوکال:
```bash
git clone https://github.com/arammoostafaye/Iptv
cd Iptv
pip install -r requirements.txt

# تست سریع (100 کانال اول)
IPTV_LIMIT=100 python update_iptv_v2.py

# اجرای کامل
python update_iptv_v2.py

# با پریمیوم
echo "http://..." > premium_sources.txt
python update_iptv_v2.py
```

---

### 🏗️ معماری V2

```
Iptv/
├── sources/
│   ├── free_sources.py       # 35+ سورس رایگان
│   ├── xtream_scraper.py     # شکارچی اکانت پریمیوم
│   ├── telegram_scraper.py   # اسکرپ تلگرام
│   └── github_scraper.py     # اسکرپ گیتهاب
├── core/
│   ├── checker.py            # چک پیشرفته HLS
│   ├── classifier.py         # دسته بندی Language-First
│   └── logo_resolver.py      # حل لوگو از iptv-org
├── web/
│   └── index.html            # پلیر تحت وب
├── output/                   # خروجی های اضافی
├── update_iptv_v2.py         # اسکریپت اصلی V2
├── update_iptv.py            # اسکریپت قدیمی (سازگار)
├── list.m3u                  # فول
├── kurdish.m3u               # فقط کردی
├── persian.m3u               # فقط فارسی
├── kurdish-persian.m3u       # ترکیبی محبوب
├── sports.m3u                # ورزشی
└── channels.json             # JSON API
```

---

### 📊 آمار زنده

<!-- این بخش توسط Actions آپدیت میشود -->
- Total: از `channels.json` بخوان
- Update: هر 6 ساعت
- Checker: Advanced HLS validation + VLC fallback
- Logo: iptv-org API + Brand fallback

---

### 🔗 لینک‌های مفید

- [Web Player](https://arammoostafaye.github.io/Iptv/)
- [Full Playlist](https://raw.githubusercontent.com/arammoostafaye/Iptv/main/list.m3u)
- [Kurdish Only](https://raw.githubusercontent.com/arammoostafaye/Iptv/main/kurdish.m3u)
- [Persian Only](https://raw.githubusercontent.com/arammoostafaye/Iptv/main/persian.m3u)
- [JSON API](https://raw.githubusercontent.com/arammoostafaye/Iptv/main/channels.json)

---

### 📄 لایسنس و هشدار

این پروژه فقط کانال‌های **Free-to-Air** و لینک‌های عمومی را جمع‌آوری می‌کند.
بخش پریمیوم فقط برای اهداف آموزشی است و اکانت‌های لو رفته را ذخیره نمی‌کند، بلکه فقط استریم‌های فیلتر شده کردی/فارسی را که در اینترنت پخش شده‌اند، بررسی می‌کند.
مسئولیت استفاده بر عهده کاربر است.

**Made with ❤️ for Kurdish & Persian community**
