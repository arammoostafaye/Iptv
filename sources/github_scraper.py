"""
GitHub Code Search Scraper
پیدا کردن اکانت های لو رفته در GitHub Gists و Repos

نیاز: GitHub Token با دسترسی search

Dork های قدرتمند:
- get.php?username= password type=m3u_plus
- xtream codes free 2026
- player_api.php username password
- extension:txt "get.php?username"

این اسکرپر هر 6 ساعت اجرا میشود و اکانت های جدید پیدا میکند
"""
import os
import re
import time
import requests
from typing import List, Set

class GitHubScraper:
    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AnonTV-Scraper"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        
        self.found_links: Set[str] = set()

    def search_code(self, query: str, per_page: int = 30, max_pages: int = 2) -> List[str]:
        """سرچ در GitHub Code Search"""
        if not self.token:
            print("⚠️ GITHUB_TOKEN not set, skipping GitHub search")
            return []

        all_items = []
        for page in range(1, max_pages + 1):
            url = f"https://api.github.com/search/code?q={requests.utils.quote(query)}&per_page={per_page}&page={page}"
            try:
                r = requests.get(url, headers=self.headers, timeout=20)
                if r.status_code == 403:
                    print("⚠️ GitHub API rate limit hit, waiting 60s...")
                    time.sleep(60)
                    continue
                if r.status_code != 200:
                    print(f"⚠️ GitHub search error {r.status_code}: {r.text[:200]}")
                    break
                
                data = r.json()
                items = data.get("items", [])
                if not items:
                    break
                all_items.extend(items)
                print(f"  🔍 Query '{query}' page {page} -> {len(items)} results")
                
                # Rate limit respect
                time.sleep(3)
                
            except Exception as e:
                print(f"⚠️ GitHub search error: {e}")
                break
        
        return all_items

    def extract_links_from_items(self, items: List[dict]) -> List[str]:
        """از نتایج سرچ، لینک های Xtream را استخراج کن"""
        from .xtream_scraper import XtreamScraper
        scraper = XtreamScraper()
        links = []
        
        for item in items[:50]:  # محدود برای جلوگیری از overload
            html_url = item.get("html_url", "")
            if not html_url:
                continue
            
            # تبدیل به raw URL
            raw_url = html_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            
            try:
                r = requests.get(raw_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    text = r.text
                    found = scraper.extract_from_text(text)
                    if found:
                        print(f"    📄 {html_url[:60]}... -> {len(found)} links")
                        links.extend(found)
                time.sleep(1)  # احترام به rate limit
            except Exception as e:
                # print(f"    ⚠️ Failed to fetch {raw_url}: {e}")
                continue
        
        unique = list(set(links))
        print(f"  ✅ Extracted {len(unique)} unique Xtream links from {len(items)} files")
        return unique

    def scrape_all(self) -> List[str]:
        """اجرای تمام Dork ها"""
        queries = [
            "get.php?username= password type=m3u_plus",
            "get.php?username= password output=ts",
            "player_api.php?username= password",
            "\"xtream codes\" free",
            "xtream iptv free 2026",
            "extension:txt \"get.php?username\"",
        ]
        
        all_links = []
        print(f"🔍 GitHub Scraper starting with {len(queries)} queries...")
        
        for q in queries:
            items = self.search_code(q, per_page=20, max_pages=1)
            if items:
                links = self.extract_links_from_items(items)
                all_links.extend(links)
            time.sleep(5)  # بین هر query صبر کن
        
        unique = list(set(all_links))
        print(f"\n🎯 TOTAL GitHub links: {len(unique)}")
        self.found_links.update(unique)
        return unique

    def save_to_file(self, links: List[str], filepath: str = "github_premium.txt"):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# GitHub scraped - {len(links)} links\n")
            f.write(f"# Generated at {__import__('datetime').datetime.utcnow().isoformat()}\n\n")
            for link in links:
                f.write(link + "\n")
        print(f"💾 Saved {len(links)} links to {filepath}")

# CLI
if __name__ == "__main__":
    scraper = GitHubScraper()
    links = scraper.scrape_all()
    scraper.save_to_file(links)
