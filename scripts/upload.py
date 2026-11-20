
import os
import asyncio
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeFilename

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION_STRING"]

CHUNKS = Path("chunks")

async def main():
    client = TelegramClient(
        StringSession(SESSION),
        API_ID,
        API_HASH
    )

    await client.start()

    me = await client.get_me()
    print(f"Logged in: {me.username or me.id}")

    # Create a private channel
    print("Creating private channel...")

    result = await client(
        CreateChannelRequest(
            title="File Transfer Storage",
            about="Private file transfer archive",
            megagroup=False
        )
    )

    channel = result.chats[0]

    print("Channel created successfully")
    print("Channel ID:", channel.id)

    files = sorted(
        p for p in CHUNKS.iterdir()
        if p.is_file()
    )

    if not files:
        print("No chunks found")
        await client.disconnect()
        return 1

    print(f"Found {len(files)} chunks")

    # Upload files
    success = 0
    failed = 0

    for index, path in enumerate(files, 1):
        size = path.stat().st_size / (1024 * 1024)

        caption = (
            f"File part {index}/{len(files)}\n"
            f"Name: {path.name}\n"
            f"Size: {size:.2f} MB"
        )

        print(
            f"Uploading {index}/{len(files)}: "
            f"{path.name}"
        )

        while True:
            try:
                await client.send_file(
                    entity=channel,
                    file=str(path),
                    caption=caption,
                    force_document=True,
                    attributes=[
                        DocumentAttributeFilename(path.name)
                    ],
                    part_size_kb=512
                )

                success += 1
                print("Upload successful")
                break

            except FloodWaitError as error:
                print(
                    f"FloodWait: waiting "
                    f"{error.seconds} seconds"
                )
                await asyncio.sleep(error.seconds + 2)

            except Exception as error:
                failed += 1
                print(
                    f"Upload failed: "
                    f"{type(error).__name__}: {error}"
                )
                break

    print("\n========== RESULT ==========")
    print("Channel:", channel.title)
    print("Channel ID:", channel.id)
    print("Success:", success)
    print("Failed:", failed)

    await client.disconnect()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
