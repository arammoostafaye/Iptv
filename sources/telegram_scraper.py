"""
Telegram IPTV Scraper
اسکرپ خودکار از کانال های تلگرام - بهترین منبع برای اکانت های تازه لو رفته

نیاز: pip install telethon

نحوه استفاده:
1. به my.telegram.org برو و API_ID و API_HASH بگیر
2. در GitHub Secrets بگذار: TG_API_ID, TG_API_HASH
3. اسکریپت خودش سشن میسازد

کانال های پیشنهادی (2026 فعال):
- @IPTV_M3U_WORLD
- @xtream_iptv_free
- @freeiptv2026
- @iptvpremiumfree
- @iptv_tools
"""
import os
import re
import asyncio
from typing import List, Set

# لیست کانال های فعال - کاربر میتواند اضافه کند
DEFAULT_CHANNELS = [
    "IPTV_M3U_WORLD",
    "xtream_iptv_free",
    "freeiptv2026",
    "iptvpremiumfree",
    "iptv_tools",
    "freeiptvtest",
    "xtream_codes_free",
    "iptvcat",
]

XTREAM_REGEX = re.compile(
    r"https?://[^\s\"'<>]+\.php\?username=[^\s\"'&<>]+&password=[^\s\"'&<>]+",
    re.I
)

class TelegramScraper:
    def __init__(self, api_id: int = None, api_hash: str = None):
        self.api_id = api_id or int(os.getenv("TG_API_ID", "0"))
        self.api_hash = api_hash or os.getenv("TG_API_HASH", "")
        self.found_links: Set[str] = set()

    async def scrape_channel(self, channel_username: str, limit: int = 500) -> List[str]:
        """اسکرپ یک کانال تلگرام"""
        try:
            from telethon import TelegramClient
        except ImportError:
            print("❌ telethon not installed. Run: pip install telethon")
            return []

        if not self.api_id or not self.api_hash:
            print("❌ TG_API_ID / TG_API_HASH not set in env")
            return []

        client = TelegramClient('anon_telegram_session', self.api_id, self.api_hash)
        await client.start()
        
        links = []
        print(f"📡 Scraping Telegram @{channel_username} (limit {limit})...")
        
        try:
            async for message in client.iter_messages(channel_username, limit=limit):
                text = message.text or ""
                if not text:
                    continue
                
                # استخراج لینک های Xtream
                for m in XTREAM_REGEX.findall(text):
                    m = m.strip().rstrip('.,;)"\'')
                    if "get.php" in m and len(m) < 300:
                        if "type=" not in m.lower():
                            m += "&type=m3u_plus&output=ts"
                        links.append(m)
                
                # همچنین فرمت های دیگر: Host:Port User Pass
                # مثال: http://example.com:8080 username: test password: 1234
                # این را با XtreamScraper.extract_from_text هم میتوان گرفت
                from .xtream_scraper import XtreamScraper
                scraper = XtreamScraper()
                extra = scraper.extract_from_text(text)
                links.extend(extra)

        except Exception as e:
            print(f"⚠️ Telegram scrape error @{channel_username}: {e}")
        
        await client.disconnect()
        
        unique = list(set(links))
        print(f"  ✅ @{channel_username} -> {len(unique)} links")
        self.found_links.update(unique)
        return unique

    async def scrape_all(self, channels: List[str] = None, limit_per_channel: int = 300) -> List[str]:
        """اسکرپ تمام کانال ها"""
        channels = channels or DEFAULT_CHANNELS
        all_links = []
        
        for ch in channels:
            try:
                links = await self.scrape_channel(ch, limit=limit_per_channel)
                all_links.extend(links)
                # تاخیر کوتاه برای جلوگیری از FloodWait
                await asyncio.sleep(2)
            except Exception as e:
                print(f"⚠️ Failed @{ch}: {e}")
                continue
        
        unique = list(set(all_links))
        print(f"\n🎯 TOTAL Telegram links: {len(unique)} from {len(channels)} channels")
        return unique

    def save_to_file(self, links: List[str], filepath: str = "telegram_premium.txt"):
        """ذخیره به فایل"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Telegram scraped - {len(links)} links\n")
            f.write(f"# Generated at {__import__('datetime').datetime.utcnow().isoformat()}\n\n")
            for link in links:
                f.write(link + "\n")
        print(f"💾 Saved {len(links)} links to {filepath}")

# CLI
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Telegram IPTV Scraper")
    parser.add_argument("--channels", nargs="+", default=DEFAULT_CHANNELS, help="Channel usernames")
    parser.add_argument("--limit", type=int, default=300, help="Messages per channel")
    parser.add_argument("--output", default="telegram_premium.txt", help="Output file")
    args = parser.parse_args()

    scraper = TelegramScraper()
    links = await scraper.scrape_all(args.channels, args.limit)
    scraper.save_to_file(links, args.output)

if __name__ == "__main__":
    asyncio.run(main())
