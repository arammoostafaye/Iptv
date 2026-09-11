"""
Logo & EPG Resolver
حل لوگو و EPG برای کانال ها

منابع:
- iptv-org API: https://iptv-org.github.io/api/channels.json
- iptv-org EPG: https://iptv-org.github.io/epg/guides.json
"""
import requests
import re
from typing import Dict

BRAND_LOGO = "https://raw.githubusercontent.com/arammoostafaye/Iptv/main/assets/logo.png"

class LogoResolver:
    def __init__(self):
        self.logo_map: Dict[str, str] = {}
        self.loaded = False

    def load(self) -> Dict[str, str]:
        """لود لوگوها از iptv-org API - V2 با logos.json"""
        try:
            print("🎨 Loading logos from iptv-org API...")
            # روش 1: channels.json جدید که logo دارد
            try:
                r = requests.get("https://iptv-org.github.io/api/channels.json", timeout=20)
                r.raise_for_status()
                data = r.json()
                for ch in data:
                    cid = ch.get("id", "").lower()
                    logo = ch.get("logo", "")
                    if cid and logo:
                        self.logo_map[cid] = logo
                        base_id = cid.split("@")[0]
                        if base_id not in self.logo_map:
                            self.logo_map[base_id] = logo
                print(f"  ✅ Loaded {len(self.logo_map)} logos from channels.json")
            except Exception as e:
                print(f"  ⚠️ channels.json failed: {e}")

            # روش 2: logos.json - دقیق تر
            try:
                r = requests.get("https://iptv-org.github.io/api/logos.json", timeout=20)
                r.raise_for_status()
                logos = r.json()
                count = 0
                for item in logos:
                    if not item.get("in_use", True):
                        continue
                    cid = item.get("channel", "").lower()
                    url = item.get("url", "")
                    if cid and url and cid not in self.logo_map:
                        self.logo_map[cid] = url
                        base = cid.split("@")[0]
                        if base not in self.logo_map:
                            self.logo_map[base] = url
                        count += 1
                print(f"  ✅ Added {count} logos from logos.json - total {len(self.logo_map)}")
            except Exception as e:
                print(f"  ⚠️ logos.json failed: {e}")

            self.loaded = True
        except Exception as e:
            print(f"  ⚠️ Logo load failed: {e}")
            self.logo_map = {}
        
        return self.logo_map

    def resolve(self, channel: dict) -> str:
        """پیدا کردن لوگوی مناسب برای یک کانال"""
        if not self.loaded:
            self.load()

        attrs = channel.get("attrs", {})
        
        # 1. اگر خودش لوگو دارد و معتبر است
        existing = attrs.get("tvg-logo", "")
        if existing and existing.startswith("http") and "logo.png" not in existing:
            return existing

        # 2. از tvg-id پیدا کن
        tvg_id = attrs.get("tvg-id", "").lower()
        if tvg_id:
            # دقیقا
            if tvg_id in self.logo_map:
                return self.logo_map[tvg_id]
            # بدون @
            base = tvg_id.split("@")[0]
            if base in self.logo_map:
                return self.logo_map[base]

        # 3. از نام کانال حدس بزن (ساده)
        name = channel.get("name", "").lower()
        # مثلا اگر Rudaw است
        for cid, logo in self.logo_map.items():
            if cid in name or name in cid:
                if len(cid) > 3:  # جلوگیری از false positive کوتاه
                    return logo

        # 4. Fallback به لوگوی برند
        return BRAND_LOGO

    def resolve_batch(self, channels: list) -> list:
        """حل لوگو برای همه کانال ها"""
        if not self.loaded:
            self.load()
        
        resolved = 0
        for ch in channels:
            logo = self.resolve(ch)
            if logo != BRAND_LOGO:
                resolved += 1
            ch["attrs"]["tvg-logo"] = logo
        
        print(f"🎨 Logo resolved: {resolved}/{len(channels)} custom, {len(channels)-resolved} brand fallback")
        return channels

class EPGResolver:
    """EPG - فعلا ساده، در آینده XMLTV میسازد"""
    def __init__(self):
        self.guides = []

    def load_guides(self):
        try:
            r = requests.get("https://iptv-org.github.io/epg/guides.json", timeout=15)
            self.guides = r.json()
            print(f"📺 Loaded {len(self.guides)} EPG guides")
        except Exception as e:
            print(f"⚠️ EPG load failed: {e}")
            self.guides = []

    def get_epg_url_for_channel(self, tvg_id: str) -> str:
        """پیدا کردن EPG URL برای یک کانال (اگر موجود باشد)"""
        # فعلا یک EPG کلی برمیگردانیم
        # در آینده میتوان XMLTV ساخت
        return "https://iptv-org.github.io/epg/guides.json"

# Singleton
_logo_resolver = None
def get_logo_resolver():
    global _logo_resolver
    if _logo_resolver is None:
        _logo_resolver = LogoResolver()
    return _logo_resolver
