import requests
import os
import hashlib
import json
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# تلگرام
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}

# منابع M3U
SOURCES = [
    "https://iptv-org.github.io/iptv/languages/fas.m3u",
    "https://iptv-org.github.io/iptv/languages/kur.m3u",
    "https://iptv-org.github.io/iptv/countries/ir.m3u",
    "https://iptv-org.github.io/iptv/countries/iq.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u"
]

OUTPUT_FILE = "list.m3u"
OUTPUT_JSON = "channels.json"

# لیست هدف: فارسی و کوردی
TARGET_CHANNELS = [
    # کوردی
    "Arian TV", "NRT", "Parto", "Roj TV", "TRT Kurdî", "Tishk TV", "Rudaw", "Ronahi TV",
    "Zaro", "Zarok TV", "Jin TV", "Atrak", "Ilam TV", "Zagros TV", "Sahar Kurdish",
    "Kordestan TV", "Mahabad TV", "Kurdistan TV", "Kurdistan 24", "Kurd Channel", "Komala",
    "Med TV", "Newroz TV", "Kurdsat", "Gali Kurdistan", "Kirkuk TV", "Badinansat",
    "Kurdmax", "Cira TV", "Freedom TV", "Med Muzik", "Sterk TV", "KNN", "Waar", "Payam TV",
    "Speda TV", "Ava TV", "Bangawaz", "Helhelok TV", "VIN TV", "Xendan", "Rojava TV",
    "NET TV", "Korek TV", "Kanal 4", "Duhok TV", "Qellat", "GEM KURD", "Salahaddin TV",
    "Babylon",
    # فارسی
    "BBC Persian", "Iran International", "VOA Persian", "Manoto", "GEM TV", "GEM Series",
    "GEM Classic", "GEM Junior", "Persiana", "Persiana Sports", "MBC Persia", "AVA Family",
    "AVA Series", "AVA Music", "Show TV", "Cheshmandaz", "Taposh", "Radio Farda",
    "Afghanistan International", "TOLO TV", "Lemar TV", "Nour", "Kurdistan 24", "Rudaw",
    "NRT", "TRT Kurdî",
    # شبکه‌های داخلی ایران
    "شبکه یک", "شبکه دو", "شبکه سه", "شبکه چهار", "شبکه پنج", "شبکه خبر", "شبکه خبر ۲",
    "شبکه آموزش", "شبکه قرآن", "شبکه مستند", "شبکه نسیم", "شبکه نمایش", "شبکه کودک",
    "شبکه امید", "شبکه افق", "شبکه سلامت", "شبکه ورزش", "شبکه تماشا", "شبکه آی‌فیلم",
    "شبکه سپهر", "شبکه فراتر", "Press TV", "شبکه العالم", "شبکه سحر", "شبکه الکوثر",
    "Hispan TV",
    # کانال‌های آنلاین فارسی
    "National Geographic", "Bplus", "Videogard", "Zoom P", "Shad TV"
]

# دسته‌بندی گروه
def categorize(channel_name):
    name = channel_name.lower()
    if any(k.lower() in name for k in ["kurd", "rudaw", "nrt", "trt", "avan", "tishk", "rozh"]):
        return "Kurdish"
    return "Persian"

# بررسی لینک فعال سریع
def is_working_parallel(url):
    try:
        r = requests.head(url, timeout=2, allow_redirects=True)
        return r.status_code == 200
    except:
        return False

# دانلود M3U
def download(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

# استخراج کانال‌ها
def parse_m3u(content):
    lines = content.splitlines()
    channels = []
    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            if i + 1 < len(lines):
                link = lines[i + 1].strip()
                if link.startswith("http"):
                    channels.append((lines[i], link))
    return channels

# ساخت لیست نهایی با فیلتر هدفمند و پوشه‌بندی
def build_playlist():
    unique_links = set()
    final_channels = []

    for source in SOURCES:
        try:
            print(f"Downloading: {source}")
            content = download(source)
            channels = parse_m3u(content)

            link_map = {link: extinf for extinf, link in channels}

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(is_working_parallel, link): link for link in link_map}

                for future in as_completed(futures):
                    link = futures[future]
                    try:
                        working = future.result()
                    except:
                        working = False

                    if not working or link in unique_links:
                        continue

                    extinf = link_map[link]
                    channel_name = re.sub(r'#EXTINF:-1.*?,', '', extinf).strip()
                    if not any(tc.lower() in channel_name.lower() for tc in TARGET_CHANNELS):
                        continue

                    group = categorize(channel_name)
                    if 'group-title="' in extinf:
                        parts = extinf.split('group-title=')
                        extinf = parts[0] + f'group-title="{group}",' + parts[1].split(",",1)[1]
                    else:
                        extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')

                    unique_links.add(link)
                    final_channels.append((extinf, link))

        except Exception as e:
            print(f"Source error: {source} → {e}")

    # مرتب‌سازی الفبایی
    final_channels.sort(key=lambda x: re.sub(r'#EXTINF:-1.*?,', '', x[0]).lower())
    return final_channels

# ذخیره M3U و JSON
def write_playlist(channels):
    # M3U
    content = "#EXTM3U\n"
    for extinf, link in channels:
        content += f"{extinf}\n{link}\n"

    new_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    old_hash = None
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "rb") as f:
            old_hash = hashlib.md5(f.read()).hexdigest()

    updated = False
    if new_hash != old_hash:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        updated = True

    # JSON
    data = [{"name": re.sub(r'#EXTINF:-1.*?,', '', x[0]).strip(), "stream": x[1]} for x in channels]
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.utcnow().isoformat(),
            "total": len(data),
            "channels": data
        }, f, indent=2)

    return updated

# تلگرام
def send_telegram(total, updated):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing.")
        return

    status = "Updated" if updated else "No Change"
    message = (
        f"📡 IPTV Auto Update\n"
        f"Status: {status}\n"
        f"Total Channels: {total}\n"
        f"UTC Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=15
        )
        print("Telegram status code:", response.status_code)
        print("Telegram response:", response.text)
    except Exception as e:
        print("Telegram send error:", e)

# Main
def main():
    print("Starting IPTV build process...")
    channels = build_playlist()
    print(f"Collected channels: {len(channels)}")
    updated = write_playlist(channels)
    send_telegram(len(channels), updated)
    print("Process completed.")

if __name__ == "__main__":
    main()
