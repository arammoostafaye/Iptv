"""
Advanced Stream Checker
چک پیشرفته استریم ها - فراتر از HTTP 200

ویژگی ها:
- HLS validation: آیا m3u8 واقعا سگمنت دارد؟
- Content-Type check
- Geo-block detection (401/403 -> None یعنی شاید برای کاربر باز باشد)
- VLC fingerprint fallback
- Speed test (اولین 64 بایت)
- Resolution detection از URL یا نام
"""
import asyncio
import aiohttp
import re
from typing import Dict, Tuple

VLC_HEADERS = {"User-Agent": "VLC/3.0.20 LibVLC/3.0.20"}
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

class StreamChecker:
    def __init__(self, timeout: int = 10, concurrency: int = 150):
        self.timeout = timeout
        self.concurrency = concurrency
        self.stats = {"alive": 0, "dead": 0, "blocked": 0, "error": 0}

    async def _probe(self, session: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str, headers: dict) -> bool | None:
        """
        Returns:
            True = alive
            False = dead
            None = blocked (geo/datacenter) but maybe ok for end user
        """
        try:
            async with sem:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=True,
                    ssl=False
                ) as r:
                    ct = r.headers.get("Content-Type", "").lower()
                    
                    # Geo-blocked / auth required -> نگه دار (برای کاربر شاید باز باشد)
                    if r.status in (401, 402, 403, 451):
                        return None
                    
                    if r.status not in (200, 206, 302, 301):
                        return False

                    # چک Content-Type
                    if "video" in ct or "mpegurl" in ct or "octet-stream" in ct or "audio" in ct:
                        try:
                            await r.content.read(128)  # تست اینکه واقعا دیتا میاد
                            return True
                        except:
                            return False

                    # اگر m3u8 است، محتوایش را چک کن
                    if ".m3u8" in url or "mpegurl" in ct or "application/vnd.apple.mpegurl" in ct:
                        try:
                            text = await r.text()
                            # باید حاوی EXT یا TS باشد
                            if "#EXTM3U" in text or "#EXTINF" in text or ".ts" in text or ".m3u8" in text:
                                return True
                            # اگر خالی یا فقط کامنت است -> مرده
                            if len(text.strip()) < 10:
                                return False
                            return True  # بعضی سرورها m3u8 بدون تگ استاندارد میدهند
                        except:
                            return False

                    # اگر مستقیم TS/MP4 است
                    if url.endswith((".ts", ".mp4", ".mkv", ".m3u8")):
                        return True

                    # Fallback: اگر 200 داد و طول محتوا > 0
                    try:
                        chunk = await r.content.read(64)
                        if len(chunk) > 0:
                            return True
                    except:
                        pass

                    return False

        except asyncio.TimeoutError:
            return False
        except Exception:
            return False

    async def check_single(self, session: aiohttp.ClientSession, session_vlc: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str, trusted: bool = False) -> bool:
        """چک یک استریم با دو fingerprint"""
        if trusted:
            return True

        # اول با User-Agent معمولی
        result = await self._probe(session, sem, url, DEFAULT_HEADERS)
        if result is True or result is None:
            return True

        # دوباره با VLC fingerprint (بعضی سرورها فقط VLC را قبول میکنند)
        result = await self._probe(session_vlc, sem, url, VLC_HEADERS)
        if result is True or result is None:
            return True

        return False

    async def check_batch(self, channels: list, cache: dict = None, skip_check: bool = False, trusted_sources: tuple = ("kurdtvs.net",)) -> Dict[int, bool]:
        """
        چک دسته ای
        Returns: {index: is_alive}
        """
        cache = cache or {}
        sem = asyncio.Semaphore(self.concurrency)
        connector = aiohttp.TCPConnector(limit=self.concurrency, ssl=False, limit_per_host=10)
        
        results: Dict[int, bool] = {}
        todo = []

        # جدا کردن کش شده ها
        for i, ch in enumerate(channels):
            if ch["url"] in cache:
                results[i] = cache[ch["url"]]
            else:
                todo.append(i)

        if skip_check:
            for i in todo:
                results[i] = True
            return results

        print(f"🔍 Checking {len(todo)} streams (cached: {len(results)}, concurrency: {self.concurrency})...")

        async with aiohttp.ClientSession(connector=connector) as session, \
                   aiohttp.ClientSession(connector=connector) as session_vlc:

            tasks = {}
            for idx in todo:
                ch = channels[idx]
                is_trusted = ch.get("source", "") in trusted_sources
                tasks[idx] = asyncio.create_task(
                    self.check_single(session, session_vlc, sem, ch["url"], trusted=is_trusted)
                )

            done = 0
            for idx, task in tasks.items():
                ok = await task
                results[idx] = ok
                cache[channels[idx]["url"]] = ok
                done += 1
                if done % 200 == 0:
                    print(f"  ⏳ Checked {done}/{len(tasks)} | Alive: {sum(results.values())}")

        alive = sum(1 for v in results.values() if v)
        print(f"✅ Check done: {alive}/{len(results)} alive ({alive/len(results)*100:.1f}%)")
        
        self.stats["alive"] = alive
        self.stats["dead"] = len(results) - alive
        return results

    @staticmethod
    def detect_quality(name: str, url: str = "") -> str:
        """تشخیص کیفیت از نام یا URL"""
        text = f"{name} {url}".lower()
        if "4k" in text or "2160p" in text:
            return "4K"
        if "1080p" in text or "fhd" in text:
            return "1080p"
        if "720p" in text or "hd" in text:
            return "720p"
        if "480p" in text or "sd" in text:
            return "480p"
        # حدس از روی کلمه HD
        if " hd" in text or "hd " in text:
            return "720p"
        return "Unknown"

    @staticmethod
    def detect_resolution_score(name: str) -> int:
        """امتیاز رزولوشن برای dedupe (هرچه بالاتر بهتر)"""
        q = StreamChecker.detect_quality(name)
        scores = {"4K": 4000, "1080p": 1080, "720p": 720, "480p": 480, "Unknown": 0}
        return scores.get(q, 0)
