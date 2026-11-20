
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


def load_uploaded():
    if STATE_FILE.exists():
        return set(STATE_FILE.read_text().splitlines())
    return set()


def mark_uploaded(name):
    with STATE_FILE.open("a") as f:
        f.write(name + "\n")


async def main():

    if not CHUNKS_DIR.exists():
        print("❌ پوشه chunks پیدا نشد.")
        return 1

    files = sorted(
        p for p in CHUNKS_DIR.rglob("*")
        if p.is_file()
    )

    if not files:
        print("❌ هیچ فایلی برای آپلود وجود ندارد.")
        return 1

    uploaded = load_uploaded()

    print(f"📦 تعداد کل تکه‌ها: {len(files)}")

    client = TelegramClient(
        StringSession(SESSION),
        API_ID,
        API_HASH
    )

    await client.start()

    me = await client.get_me()

    print(f"✅ ورود موفق: @{me.username or me.id}")

    ok = 0
    fail = 0

    for i, path in enumerate(files, 1):

        name = path.name

        if name in uploaded:
            print(f"⏭️ [{i}/{len(files)}] قبلاً آپلود شده")
            ok += 1
            continue

        size_mb = path.stat().st_size / (1024 * 1024)

        caption = f"{PREFIX} — {name} ({size_mb:.1f} MB)"

        print(
            f"⬆️ [{i}/{len(files)}] "
            f"{name} ({size_mb:.1f} MB)"
        )

        try:

            await client.send_file(
                entity=CHANNEL,
                file=str(path),
                caption=caption,
                attributes=[
                    DocumentAttributeFilename(name)
                ],
                force_document=True,
            )

            mark_uploaded(name)
            ok += 1

            print("✅ آپلود موفق")

        except FloodWaitError as e:

            print(f"⏳ محدودیت تلگرام: {e.seconds} ثانیه")

            await asyncio.sleep(e.seconds + 2)

            try:

                await client.send_file(
                    entity=CHANNEL,
                    file=str(path),
                    caption=caption,
                    attributes=[
                        DocumentAttributeFilename(name)
                    ],
                    force_document=True,
                )

                mark_uploaded(name)
                ok += 1

                print("✅ آپلود موفق پس از انتظار")

            except Exception as error:
                fail += 1
                print(f"❌ خطا: {error}")

        except Exception as error:

            fail += 1

            print(
                f"❌ {type(error).__name__}: {error}"
            )

    await client.disconnect()

    print("\n========== نتیجه ==========")
    print(f"موفق: {ok}")
    print(f"ناموفق: {fail}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
