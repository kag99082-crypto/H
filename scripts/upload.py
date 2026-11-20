#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeFilename


API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION_STRING"]
CHANNEL = os.environ["CHANNEL_ID"]
PREFIX = os.environ.get("CAPTION_PREFIX", "part")

CHUNKS_DIR = Path("chunks")
STATE_FILE = Path("uploaded.txt")


def load_uploaded() -> set:
    if STATE_FILE.exists():
        return set(STATE_FILE.read_text().splitlines())
    return set()


def mark_uploaded(name: str) -> None:
    with STATE_FILE.open("a") as f:
        f.write(name + "\n")


async def main() -> int:
    if not CHUNKS_DIR.exists():
        print("❌ پوشه chunks پیدا نشد.")
        return 1

    files = sorted([p for p in CHUNKS_DIR.iterdir() if p.is_file()])
    if not files:
        print("❌ فایلی برای آپلود نیست.")
        return 1

    total = len(files)
    print(f"📦 {total} تکه برای آپلود.")

    uploaded = load_uploaded()
    if uploaded:
        print(f"♻️ {len(uploaded)} تکه قبلاً آپلود شده بود، رد می‌شوند.")

    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"✅ وارد شدیم: @{me.username or me.id}")

    ok, fail = 0, 0
    for i, path in enumerate(files, 1):
        name = path.name
        if name in uploaded:
            print(f"⏭️  [{i}/{total}] {name} قبلاً آپلود شده")
            ok += 1
            continue

        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"⬆️  [{i}/{total}] {name} ({size_mb:.1f} MB) ...")

        caption = f"{PREFIX} — {name} ({size_mb:.1f} MB)"
        try:
            await client.send_file(
                entity=CHANNEL,
                file=str(path),
                caption=caption,
                attributes=[DocumentAttributeFilename(name)],
                force_document=True,
            )
            mark_uploaded(name)
            ok += 1
            print(f"   ✅ آپلود شد.")
        except FloodWaitError as e:
            print(f"   ⏳ FloodWait {e.seconds}s ...")
            await asyncio.sleep(e.seconds)
            try:
                await client.send_file(
                    entity=CHANNEL,
                    file=str(path),
                    caption=caption,
                    attributes=[DocumentAttributeFilename(name)],
                    force_document=True,
                )
                mark_uploaded(name)
                ok += 1
                print(f"   ✅ آپلود شد (بعد از انتظار).")
            except Exception as e2:
                fail += 1
                print(f"   ❌ ناموفق: {type(e2).__name__}: {e2}")
        except Exception as e:
            fail += 1
            print(f"   ❌ ناموفق: {type(e).__name__}: {e}")

    await client.disconnect()
    print(f"\n📊 نتیجه: موفق={ok}  ناموفق={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
