
#!/usr/bin/env python3

import requests
import random
import sys
import time
import json
from pathlib import Path

API_URL = "https://telegramdownloader.net/proxy.php"

PROXY_LIST = (
    "https://raw.githubusercontent.com/"
    "ProxyScraper/ProxyScraper/main/http.txt"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://telegramdownloader.net",
    "Referer": "https://telegramdownloader.net/"
}


def get_proxy_list():
    print("📡 Downloading fresh proxy list...")

    response = requests.get(PROXY_LIST, timeout=30)
    response.raise_for_status()

    proxies = list(dict.fromkeys(
        line.strip()
        for line in response.text.splitlines()
        if line.strip() and ":" in line
    ))

    random.shuffle(proxies)

    print(f"📦 Found {len(proxies)} proxy candidates")
    return proxies[:50]


def get_working_session(telegram_link):
    proxies = get_proxy_list()

    for index, address in enumerate(proxies, 1):
        proxy_url = f"http://{address}"

        session = requests.Session()
        session.headers.update(HEADERS)
        session.proxies.update({
            "http": proxy_url,
            "https": proxy_url
        })

        try:
            print(f"🔍 Testing proxy {index}/{len(proxies)}")

            # First check HTTPS connectivity
            check = session.get(
                "https://api.ipify.org",
                timeout=8
            )
            check.raise_for_status()

            # Then test the actual downloader API
            response = session.post(
                API_URL,
                data={"telegram_link": telegram_link},
                timeout=20
            )

            if response.status_code != 200:
                print(f"   ❌ API returned {response.status_code}")
                session.close()
                continue

            result = response.json()

            file_data = (
                result.get("data", {})
                .get("data", {})
            )

            raw_url = file_data.get("link")
            file_name = file_data.get("file_name")

            if raw_url and file_name:
                print("   ✅ Working proxy found!")
                print("   📁 File:", file_name)

                return session, raw_url, Path(file_name).name

            print("   ❌ API did not return a download link")
            session.close()

        except (requests.RequestException, ValueError) as error:
            print(f"   ⚠️ Proxy failed: {type(error).__name__}")
            session.close()

        except Exception as error:
            print(f"   ⚠️ Unexpected error: {error}")
            session.close()

    raise RuntimeError(
        "No proxy successfully returned a download link."
    )


def download_with_resume(session, url, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_suffix(
        output_path.suffix + ".partial"
    )

    downloaded = temp_path.stat().st_size if temp_path.exists() else 0

    for attempt in range(10):
        try:
            headers = {}

            if downloaded:
                headers["Range"] = f"bytes={downloaded}-"

            response = session.get(
                url,
                headers=headers,
                stream=True,
                timeout=(20, 60)
            )

            response.raise_for_status()

            # If server ignores Range, restart instead of corrupting file
            if downloaded and response.status_code == 200:
                downloaded = 0
                temp_path.unlink(missing_ok=True)

            total = int(response.headers.get("content-length", 0))

            if response.status_code == 206:
                total += downloaded

            mode = "ab" if downloaded else "wb"

            with open(temp_path, mode) as file:
                for chunk in response.iter_content(1024 * 256):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)

                        if total:
                            percent = downloaded * 100 / total
                            print(
                                f"\r📥 Download: {percent:.1f}%",
                                end="",
                                flush=True
                            )

            response.close()

            # Verify expected size when available
            if total and downloaded < total:
                raise requests.exceptions.ChunkedEncodingError(
                    "Incomplete download"
                )

            temp_path.replace(output_path)

            print("\n✅ Download completed!")
            return output_path.stat().st_size

        except requests.RequestException as error:
            print(f"\n⚠️ Download interrupted: {error}")
            print(f"Retry {attempt + 1}/10")

            time.sleep(min(2 ** attempt, 60))

            downloaded = (
                temp_path.stat().st_size
                if temp_path.exists()
                else 0
            )

    raise RuntimeError("Maximum download retries reached")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 telegram_downloader.py <telegram_link> [output_dir]")
        sys.exit(1)

    telegram_link = sys.argv[1]
    output_dir = Path(sys.argv[2] if len(sys.argv) > 2 else ".")

    session = None

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        print("🔗 Finding a working proxy...")

        session, raw_url, file_name = get_working_session(
            telegram_link
        )

        output_path = output_dir / file_name

        print("🚀 Starting download...")
        size = download_with_resume(
            session,
            raw_url,
            output_path
        )

        with open(output_dir / ".download_info", "w") as info:
            info.write(f"{file_name}\n{size}")

        print(f"📦 File: {file_name}")
        print(f"📏 Size: {size / 1_000_000:.2f} MB")

    except Exception as error:
        print(f"\n❌ ERROR: {error}")
        sys.exit(1)

    finally:
        if session:
            session.close()


if __name__ == "__main__":
    main()
