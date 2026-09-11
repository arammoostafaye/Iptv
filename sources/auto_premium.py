"""
Auto Premium Aggregator
ترکیب تمام اسکرپرها + ذخیره خودکار + تست

این اسکریپت هر روز اجرا میشود و:
1. از تلگرام 500 پیام آخر 8 کانال را میخواند
2. از گیتهاب 6 dork را سرچ میکند
3. از فایل های لوکال میخواند
4. همه را validate میکند
5. فقط 20 تای برتر را نگه میدارد (برای جلوگیری از overload)
6. در premium_sources.txt ذخیره میکند

استفاده:
  python -m sources.auto_premium --telegram --github --validate
"""
import os
import asyncio
import argparse
from typing import List, Set

from .xtream_scraper import XtreamScraper
from .telegram_scraper import TelegramScraper
from .github_scraper import GitHubScraper

class AutoPremiumAggregator:
    def __init__(self):
        self.scraper = XtreamScraper()
        self.all_links: Set[str] = set()
        self.valid_links: List[str] = []

    async def run_telegram(self, limit_per_channel: int = 300) -> List[str]:
        """اسکرپ تلگرام"""
        api_id = os.getenv("TG_API_ID")
        api_hash = os.getenv("TG_API_HASH")
        
        if not api_id or not api_hash:
            print("⏭️ Skipping Telegram - TG_API_ID/HASH not set")
            return []

        try:
            tg = TelegramScraper(api_id=int(api_id), api_hash=api_hash)
            links = await tg.scrape_all(limit_per_channel=limit_per_channel)
            print(f"📡 Telegram: {len(links)} links")
            self.all_links.update(links)
            return links
        except Exception as e:
            print(f"⚠️ Telegram failed: {e}")
            return []

    def run_github(self) -> List[str]:
        """اسکرپ گیتهاب"""
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not token:
            print("⏭️ Skipping GitHub - GITHUB_TOKEN not set")
            return []

        try:
            gh = GitHubScraper(token)
            links = gh.scrape_all()
            print(f"🔍 GitHub: {len(links)} links")
            self.all_links.update(links)
            return links
        except Exception as e:
            print(f"⚠️ GitHub failed: {e}")
            return []

    def run_local_files(self) -> List[str]:
        """خواندن از فایل های لوکال"""
        files = ["premium_sources.txt", "telegram_premium.txt", "github_premium.txt", "premium_sources.txt.example"]
        links = []
        for fp in files:
            if os.path.exists(fp):
                try:
                    found = self.scraper.load_from_file(fp)
                    links.extend(found)
                except Exception as e:
                    print(f"⚠️ Failed to load {fp}: {e}")
        print(f"📁 Local files: {len(links)} links")
        self.all_links.update(links)
        return links

    def run_paste_sources(self) -> List[str]:
        """خواندن از منابع Paste عمومی"""
        # لیستی از URL های عمومی که روزانه آپدیت میشوند
        # کاربر میتواند این لیست را گسترش دهد
        paste_urls = [
            # مثال - اینها را با منابع واقعی جایگزین کن
            # "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8" # این رایگان است نه پریمیوم
        ]
        # فعلا خالی - چون منابع پریمیوم عمومی به سرعت بن میشوند
        return []

    async def validate_all(self, max_to_validate: int = 50, concurrency: int = 30) -> List[str]:
        """اعتبارسنجی تمام لینک های جمع شده"""
        if not self.all_links:
            print("❌ No links to validate")
            return []

        to_check = list(self.all_links)[:max_to_validate]
        print(f"\n🔍 Validating top {len(to_check)} / {len(self.all_links)} total links...")
        
        valid = await self.scraper.validate_batch(to_check, concurrency=concurrency)
        self.valid_links = valid
        return valid

    def save_valid(self, filepath: str = "premium_sources.txt", keep_top: int = 20):
        """ذخیره فقط اکانت های سالم"""
        # فقط 20 تای برتر را نگه دار (جدیدترین یا با max_connections بالاتر)
        to_save = self.valid_links[:keep_top]
        
        if not to_save:
            print("⚠️ No valid links to save")
            return

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Auto-generated premium sources - {len(to_save)} valid accounts\n")
            f.write(f"# Generated at {__import__('datetime').datetime.utcnow().isoformat()} UTC\n")
            f.write(f"# Total found: {len(self.all_links)}, Valid: {len(self.valid_links)}\n\n")
            for link in to_save:
                f.write(link + "\n")

        print(f"💾 Saved {len(to_save)} valid accounts to {filepath}")

        # همچنین یک نسخه پشتیبان با تمام لینک ها (حتی invalid) برای دیباگ
        with open("premium_all_found.txt", "w", encoding="utf-8") as f:
            f.write(f"# All found - {len(self.all_links)} links\n")
            for link in self.all_links:
                f.write(link + "\n")

    async def run_full(self, enable_telegram: bool = False, enable_github: bool = False, validate: bool = True):
        """اجرای کامل"""
        print("=== 🚀 Auto Premium Aggregator ===")
        
        # 1. جمع آوری
        self.run_local_files()
        
        if enable_telegram:
            await self.run_telegram()
        
        if enable_github:
            self.run_github()
        
        self.run_paste_sources()
        
        print(f"\n📊 TOTAL FOUND: {len(self.all_links)} unique Xtream links")
        
        # 2. اعتبارسنجی
        if validate and self.all_links:
            await self.validate_all()
            self.save_valid()
        else:
            # بدون validate، فقط همه را ذخیره کن
            with open("premium_sources.txt", "w", encoding="utf-8") as f:
                for link in list(self.all_links)[:50]:
                    f.write(link + "\n")
            print(f"💾 Saved {len(self.all_links)} links without validation")

        print("\n✅ Auto Premium Aggregator done!")

async def main():
    parser = argparse.ArgumentParser(description="Auto Premium Aggregator")
    parser.add_argument("--telegram", action="store_true", help="Enable Telegram scraping")
    parser.add_argument("--github", action="store_true", help="Enable GitHub scraping")
    parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    parser.add_argument("--limit", type=int, default=300, help="Messages per Telegram channel")
    args = parser.parse_args()

    agg = AutoPremiumAggregator()
    await agg.run_full(
        enable_telegram=args.telegram,
        enable_github=args.github,
        validate=not args.no_validate
    )

if __name__ == "__main__":
    asyncio.run(main())
