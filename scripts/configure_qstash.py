from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request


def schedule_api_url(destination: str) -> str:
    # QStash treats the destination as a URL-shaped path suffix and expects
    # the http(s) scheme to remain visible rather than percent-encoded.
    return f"https://qstash.upstash.io/v2/schedules/{destination}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the QStash delivery schedule")
    parser.add_argument(
        "--url",
        default=os.getenv("APP_URL", ""),
        help="Deployed Vercel URL (or set APP_URL)",
    )
    args = parser.parse_args()

    qstash_token = os.getenv("QSTASH_TOKEN", "").strip()
    cron_secret = os.getenv("CRON_SECRET", "").strip()
    app_url = args.url.strip().rstrip("/")
    if not qstash_token or not cron_secret or not app_url:
        raise SystemExit("QSTASH_TOKEN, CRON_SECRET and APP_URL/--url are required")
    if not app_url.startswith("https://"):
        raise SystemExit("The deployed APP_URL must start with https://")

    destination = f"{app_url}/api/cron"
    request = urllib.request.Request(
        schedule_api_url(destination),
        data=b"{}",
        headers={
            "Authorization": f"Bearer {qstash_token}",
            "Content-Type": "application/json",
            "Upstash-Cron": "*/2 * * * *",
            "Upstash-Forward-Authorization": f"Bearer {cron_secret}",
            "Upstash-Method": "POST",
            "Upstash-Retries": "3",
            "Upstash-Schedule-Id": "bible-bot-delivery",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"QStash rejected the schedule: {detail}") from None

    schedule_id = result.get("scheduleId", "bible-bot-delivery")
    print(f"QStash schedule configured: {schedule_id} -> {destination}")


if __name__ == "__main__":
    main()
