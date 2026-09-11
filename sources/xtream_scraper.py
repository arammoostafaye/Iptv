"""
Xtream Codes Premium Scraper
شکارچی اکانت های پریمیوم لو رفته - قلب تپنده بخش پریمیوم

این ماژول 3 منبع دارد:
1. فایل لوکال premium_sources.txt (کاربر خودش اضافه میکند)
2. GitHub Code Search API
3. Pastebin / rentry / raw text sites

خروجی: لیست M3U های پریمیوم معتبر
"""
import re
import os
import json
import asyncio
import aiohttp
import requests
from datetime import datetime
from typing import List, Set

class XtreamScraper:
    # Regex برای پیدا کردن لینک مستقیم M3U
    XTREAM_M3U_RE = re.compile(
        r"https?://[^\s\"'<>]+\.php\?username=[^\s\"'&<>]+&password=[^\s\"'&<>]+[^\s\"'<>]*",
        re.I
    )
    # Regex برای یوزر/پسورد جدا (وقتی Host + User + Pass در خط های جدا هستند)
    XTREAM_CREDS_RE = re.compile(
        r"(https?://[^/\s:]+(?::\d+)?)[^\n]*?username[:=\s]+([A-Za-z0-9_\-]+)[^\n]*?password[:=\s]+([A-Za-z0-9_\-]+)",
        re.I | re.S
    )
    # Regex برای فرمت های دیگر: host:port:user:pass
    XTREAM_SIMPLE_RE = re.compile(
        r"(https?://[^\s:]+:\d+)\s*[:|]\s*([A-Za-z0-9]+)\s*[:|]\s*([A-Za-z0-9]+)",
        re.I
    )

    def __init__(self):
        self.found_m3us: Set[str] = set()
        self.valid_accounts: List[str] = []
        self.stats = {"found": 0, "valid": 0, "expired": 0, "dead": 0}

    def extract_from_text(self, text: str) -> List[str]:
        """از یک متن خام، تمام لینک های Xtream را استخراج کن"""
        results = []
        
        # 1. لینک مستقیم M3U
        for m in self.XTREAM_M3U_RE.findall(text):
            m = m.strip().rstrip('.,;)"\'')
            # نرمالایز: اگر type ندارد اضافه کن
            if "type=" not in m.lower():
                sep = "&" if "?" in m else "?"
                m += f"{sep}type=m3u_plus&output=ts"
            # فقط ts یا m3u_plus قبول کن
            if "get.php" in m:
                results.append(m)

        # 2. فرمت Host + username + password جدا
        for host, user, pwd in self.XTREAM_CREDS_RE.findall(text):
            host = host.rstrip('/').strip()
            if len(user) < 3 or len(pwd) < 3:
                continue
            if len(user) > 50 or len(pwd) > 50:  # جلوگیری از false positive
                continue
            m3u = f"{host}/get.php?username={user}&password={pwd}&type=m3u_plus&output=ts"
            results.append(m3u)

        # 3. فرمت ساده host:port:user:pass
        for host, user, pwd in self.XTREAM_SIMPLE_RE.findall(text):
            m3u = f"{host}/get.php?username={user}&password={pwd}&type=m3u_plus&output=ts"
            results.append(m3u)

        # Dedupe + Clean
        cleaned = []
        for r in results:
            r = r.strip()
            if len(r) > 30 and len(r) < 300 and "username=" in r and "password=" in r:
                cleaned.append(r)
        
        return list(set(cleaned))

    async def validate_xtream_account(self, session: aiohttp.ClientSession, m3u_url: str) -> dict:
        """
        آیا اکانت هنوز زنده است؟
        Returns: {"valid": bool, "exp_date": timestamp, "max_connections": int, "status": str}
        """
        try:
            # تبدیل get.php به player_api.php برای چک سریع و سبک
            api_url = m3u_url.replace("get.php", "player_api.php")
            # حذف پارامترهای اضافی
            if "&type=" in api_url:
                api_url = api_url.split("&type=")[0]
            if "?type=" in api_url:
                api_url = api_url.split("?type=")[0] + api_url[api_url.find("?type="):].split("&")[0]
                # بازسازی درست
                base = m3u_url.split("/get.php")[0]
                user = re.search(r"username=([^&]+)", m3u_url)
                pwd = re.search(r"password=([^&]+)", m3u_url)
                if user and pwd:
                    api_url = f"{base}/player_api.php?username={user.group(1)}&password={pwd.group(1)}"
            
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=12), ssl=False) as r:
                if r.status != 200:
                    return {"valid": False, "reason": f"HTTP {r.status}"}
                
                try:
                    data = await r.json(content_type=None)
                except:
                    # بعضی سرورها json نیستند، سعی کن text را parse کنی
                    txt = await r.text()
                    try:
                        data = json.loads(txt)
                    except:
                        return {"valid": False, "reason": "Invalid JSON"}

                user_info = data.get("user_info", {})
                auth = user_info.get("auth")
                status = user_info.get("status", "")
                exp_date = user_info.get("exp_date")
                max_conn = user_info.get("max_connections", "0")
                
                if auth != 1:
                    return {"valid": False, "reason": "Auth failed"}
                if status.lower() not in ("active", ""):
                    return {"valid": False, "reason": f"Status {status}"}
                
                # چک اکسپایر
                if exp_date:
                    try:
                        exp_ts = int(exp_date)
                        if exp_ts != 0 and exp_ts < datetime.utcnow().timestamp():
                            return {"valid": False, "reason": "Expired", "exp_date": exp_ts}
                    except:
                        pass

                return {
                    "valid": True,
                    "exp_date": exp_date,
                    "max_connections": max_conn,
                    "status": status,
                    "server_info": data.get("server_info", {})
                }

        except asyncio.TimeoutError:
            return {"valid": False, "reason": "Timeout"}
        except Exception as e:
            return {"valid": False, "reason": str(e)[:100]}

    async def validate_batch(self, m3u_list: List[str], concurrency: int = 50) -> List[str]:
        """اعتبارسنجی دسته ای اکانت ها"""
        print(f"🔍 Validating {len(m3u_list)} Xtream accounts...")
        sem = asyncio.Semaphore(concurrency)
        connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
        
        valid = []
        
        async def check_one(session, url):
            async with sem:
                result = await self.validate_xtream_account(session, url)
                if result["valid"]:
                    print(f"  ✅ VALID: {url[:60]}... Exp: {result.get('exp_date')}")
                    return url
                else:
                    print(f"  ❌ DEAD: {url[:50]}... Reason: {result.get('reason')}")
                    return None

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [check_one(session, url) for url in m3u_list]
            results = await asyncio.gather(*tasks)
            valid = [r for r in results if r]

        self.stats["valid"] = len(valid)
        self.stats["dead"] = len(m3u_list) - len(valid)
        print(f"✅ Validation done: {len(valid)}/{len(m3u_list)} valid")
        return valid

    def load_from_file(self, filepath: str = "premium_sources.txt") -> List[str]:
        """خواندن اکانت ها از فایل لوکال"""
        if not os.path.exists(filepath):
            print(f"⚠️ {filepath} not found, skipping")
            return []
        
        links = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            # هم خط به خط هم کل متن را چک کن (چون ممکنه فرمت های مختلف باشه)
            links.extend(self.extract_from_text(content))
            # همچنین خط به خط که مستقیم M3U هستند
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "get.php" in line and "username=" in line:
                    links.append(line.strip())
        
        unique = list(set(links))
        print(f"📁 Loaded {len(unique)} premium links from {filepath}")
        self.found_m3us.update(unique)
        return unique

    async def scrape_pastebin_sources(self) -> List[str]:
        """اسکرپ از سایت های Paste عمومی - بدون API Key"""
        paste_urls = [
            # این لیست را کاربر میتواند گسترش دهد
            "https://raw.githubusercontent.com/ferstar/Anbar_IPTV/main/Xtream.txt",
        ]
        all_links = []
        for url in paste_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                        if r.status == 200:
                            txt = await r.text()
                            found = self.extract_from_text(txt)
                            all_links.extend(found)
                            print(f"  📄 {url} -> {len(found)} links")
            except Exception as e:
                print(f"  ⚠️ Paste scrape error {url}: {e}")
        return list(set(all_links))

    async def fetch_and_filter_premium(self, session: aiohttp.ClientSession, m3u_url: str, classifier_fn, max_channels_per_account: int = 10000) -> List[dict]:
        """یک اکانت پریمیوم را دانلود کن و فقط کانال های مرتبط (کردی/فارسی) را نگه دار"""
        try:
            async with session.get(m3u_url, timeout=aiohttp.ClientTimeout(total=30), ssl=False) as r:
                if r.status != 200:
                    return []
                text = await r.text()
                if "#EXTINF" not in text:
                    return []
                
                # Parse M3U
                from .free_sources import FREE_SOURCES  # avoid circular
                channels = []
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if line.strip().startswith("#EXTINF"):
                        # استخراج attr
                        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
                        name = line.rsplit(",", 1)[-1].strip()
                        if i+1 < len(lines):
                            url = lines[i+1].strip()
                            if url.startswith("http"):
                                channels.append({"name": name, "attrs": attrs, "url": url, "source": "premium"})
                
                if len(channels) > max_channels_per_account:
                    channels = channels[:max_channels_per_account]
                
                # V2 UPGRADE: Keep ALL categories from premium (Movies, Documentary, Kids, Music, etc)
                # قبلا فقط کردی/فارسی نگه میداشتیم، الان همه را نگه میداریم
                kept = []
                for ch in channels:
                    try:
                        group = classifier_fn(ch)
                        # همه گروه ها به جز DROP را نگه دار
                        if group != "DROP":
                            ch["group"] = group
                            kept.append(ch)
                    except:
                        # اگر classifier خطا داد، به عنوان Other نگه دار
                        ch["group"] = "Other"
                        kept.append(ch)
                
                print(f"  📦 PREMIUM {m3u_url[:50]}... -> {len(kept)}/{len(channels)} kept (ALL categories)")
                return kept

        except Exception as e:
            print(f"  ⚠️ PREMIUM FETCH ERROR {m3u_url[:40]}: {e}")
            return []

# Helper برای تست سریع
async def quick_test():
    scraper = XtreamScraper()
    scraper.load_from_file("premium_sources.txt")
    if scraper.found_m3us:
        valid = await scraper.validate_batch(list(scraper.found_m3us)[:20])
        print(f"Valid: {valid}")

if __name__ == "__main__":
    asyncio.run(quick_test())
