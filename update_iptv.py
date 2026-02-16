import requests
import os
import hashlib
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}

SOURCES = [
    "https://iptv-org.github.io/iptv/languages/fas.m3u",
    "https://iptv-org.github.io/iptv/languages/kur.m3u",
    "https://iptv-org.github.io/iptv/countries/ir.m3u",
    "https://iptv-org.github.io/iptv/countries/iq.m3u"
]

OUTPUT_FILE = "premium_list.m3u"


def download_source(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


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


def categorize(extinf):
    name = extinf.lower()

    if "radio" in name:
        return None  # حذف رادیو

    if any(k in name for k in ["kurd", "rudaw", "k24", "waartv", "ava"]):
        return "Kurdish"

    if any(f in name for f in ["iran", "tehran", "fars", "shiraz", "mashhad"]):
        return "Iran"

    if any(i in name for i in ["iraq", "baghdad"]):
        return "Iraq"

    return "General"


def build_playlist():
    unique_links = set()
    final_channels = []

    for source in SOURCES:
        try:
            print(f"Downloading: {source}")
            content = download_source(source)
            channels = parse_m3u(content)

            for extinf, link in channels:

                if link in unique_links:
                    continue

                group = categorize(extinf)
                if group is None:
                    continue

                if 'group-title="' in extinf:
                    extinf = extinf.split('group-title=')[0] + f'group-title="{group}",' + extinf.split(",",1)[1]
                else:
                    extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')

                unique_links.add(link)
                final_channels.append((extinf, link))

        except Exception as e:
            print(f"Error reading {source}: {e}")

    return final_channels


def write_file(channels):
    content = "#EXTM3U\n"
    for extinf, link in channels:
        content += f"{extinf}\n{link}\n"

    new_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

    old_hash = None
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "rb") as f:
            old_hash = hashlib.md5(f.read()).hexdigest()

    if new_hash != old_hash:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def send_telegram(total, updated):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    status = "Updated" if updated else "No Change"

    message = (
        f"📡 IPTV Auto Update\n"
        f"Status: {status}\n"
        f"Total Channels: {total}\n"
        f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": message}
    )


def main():
    print("Starting IPTV Build...")

    channels = build_playlist()

    print(f"Collected channels: {len(channels)}")

    updated = write_file(channels)

    send_telegram(len(channels), updated)

    print("Done.")


if __name__ == "__main__":
    main()
