import requests
import re
import os

# دریافت متغیرهای امنیتی
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# تنظیمات اتصال
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# لیست منابع (شامل ایران، یاهست، نایل‌ست و کانال‌های کوردی)
SOURCES = [
    "https://iptv-org.github.io/iptv/languages/fas.m3u",
    "https://iptv-org.github.io/iptv/languages/kur.m3u",
    "https://iptv-org.github.io/iptv/countries/ir.m3u",
    "https://iptv-org.github.io/iptv/countries/iq.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ckb.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/kmr.m3u"
]

def check_link(url):
    try:
        # تست سریع لینک (فقط ۵ ثانیه منتظر می‌ماند)
        r = requests.get(url, headers=HEADERS, timeout=5, stream=True)
        return r.status_code == 200
    except:
        return False

def main():
    print("Starting update process...")
    unique_channels = {}
    
    for source in SOURCES:
        try:
            print(f"Checking source: {source}")
            content = requests.get(source, headers=HEADERS, timeout=10).text
            # استخراج نام و لینک
            matches = re.findall(r'(#EXTINF:.*?,(.*?)\n)(http[^\n]+)', content)
            
            for info, name, link in matches:
                link = link.strip()
                name = name.strip()
                
                # فقط اگر لینک تکراری نباشد بررسی کن
                if link not in [c['link'] for c in unique_channels.values()]:
                    if check_link(link):
                        # دسته‌بندی ساده
                        if any(x in name.lower() for x in ['kurd', 'rudaw', 'waartv', 'ava']):
                            info = info.replace('group-title=""', 'group-title="Kurdish"')
                        
                        unique_channels[name] = {'info': info, 'link': link}
        except Exception as e:
            print(f"Error reading source {source}: {e}")

    # ذخیره فایل
    with open("premium_list.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in unique_channels.values():
            f.write(f"{ch['info']}{ch['link']}\n")
            
    print(f"Total channels found: {len(unique_channels)}")

    # ارسال گزارش به تلگرام
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        msg = f"✅ لیست آپدیت شد.\nتعداد کانال‌ها: {len(unique_channels)}\nوضعیت: آماده استفاده"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

if __name__ == "__main__":
    main()
