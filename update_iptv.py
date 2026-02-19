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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*"
}

# منابع M3U (سورس‌های کوردی اضافه شد)
SOURCES = [
    "https://iptv-org.github.io/iptv/languages/fas.m3u",
    "https://iptv-org.github.io/iptv/languages/kur.m3u",
    "https://iptv-org.github.io/iptv/countries/ir.m3u",
    "https://iptv-org.github.io/iptv/countries/iq.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ckb.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/kmr.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u"
]

OUTPUT_FILE = "list.m3u"
OUTPUT_JSON = "channels.json"

# لیست جامع کلمات کلیدی برای استخراج حداکثری
KURDISH_KEYWORDS = [
    "kurd", "rudaw", "nrt", "trt", "ava", "tishk", "rozh", "waartv", "k24", 
    "kurdsat", "payam", "speda", "ark", "zaro", "ronahi", "korek", "vin", 
    "zagros", "gali", "kirkuk", "badinan", "cira", "sterk", "knn", "rojava", "net tv", "arian", "parto"
]

PERSIAN_KEYWORDS = [
    "persian", "iran", "farsi", "gem ", "manoto", "bbc", "voa", "mbc", "tapesh",
    "tolo", "lemar", "afghan", "شبکه", "irib", "varzesh", "telewebion", "radio javan", "rj tv", "itn",
    "persiana", "show tv", "cheshmandaz", "national geographic"
]

TARGET_CHANNELS = KURDISH_KEYWORDS + PERSIAN_KEYWORDS

# دسته‌بندی گروه
def categorize(channel_name):
    name = channel_name.lower()
    if any(k.lower() in name for k in KURDISH_KEYWORDS):
        return "Kurdish"
    if any(k.lower() in name for k in PERSIAN_KEYWORDS):
        return "Persian"
    return "Other"

# بررسی لینک فعال سریع
def is_working_parallel(url):
    try:
        r = requests.head(url, timeout=3, allow_redirects=True)
        return r.status_code in [200, 301, 302]
    except:
        return False

# دانلود M3U
def download(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return ""

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

# ساخت لیست نهایی با فیلتر هدفمند
def build_playlist():
    unique_links = set()
    final_channels = []

    for source in SOURCES:
        print(f"Downloading: {source}")
        content = download(source)
        if not content:
            continue
            
        channels = parse_m3u(content)
        
        # فیلتر اولیه (فقط کانال‌های کوردی و فارسی را نگه می‌دارد)
        filtered_channels = []
        for extinf, link in channels:
            channel_name = re.sub(r'#EXTINF:-1.*?,', '', extinf).strip()
            if any(tc.lower() in channel_name.lower() for tc in TARGET_CHANNELS):
                filtered_channels.append((extinf, link, channel_name))
        
        # تست موازی لینک‌ها برای سرعت بیشتر
        link_map = {item[1]: (item[0], item[2]) for item in filtered_channels}
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(is_working_parallel, link): link for link in link_map}
            for future in as_completed(futures):
                link = futures[future]
                working = future.result()
                
                if working and link not in unique_links:
                    extinf, channel_name = link_map[link]
                    group = categorize(channel_name)
                    
                    if 'group-title="' in extinf:
                        extinf = re.sub(r'group-title=".*?"', f'group-title="{group}"', extinf)
                    else:
                        extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')
                        
                    unique_links.add(link)
                    final_channels.append((extinf, link))

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
        
    status = "Updated ✅" if updated else "No Change ⚠️"
    message = (
        f"📡 IPTV Auto Update\n"
        f"Status: {status}\n"
        f"Total Channels: {total}\n"
        f"UTC Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=15)
        print("Telegram response:", response.status_code)
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
