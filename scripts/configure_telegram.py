from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request

COMMANDS = [
    {"command": "today", "description": "Получить сегодняшнюю главу"},
    {"command": "settings", "description": "Настройки рассылки"},
    {"command": "favorites", "description": "Сохранённые главы"},
    {"command": "pause", "description": "Приостановить рассылку"},
    {"command": "help", "description": "Справка"},
]


def telegram_call(token: str, method: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"Telegram rejected {method}: {detail}") from None
    if not result.get("ok"):
        description = result.get("description", "unknown error")
        raise SystemExit(f"Telegram rejected {method}: {description}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure the Telegram webhook and commands")
    parser.add_argument(
        "--url",
        default=os.getenv("APP_URL", ""),
        help="Deployed Vercel URL (or set APP_URL)",
    )
    args = parser.parse_args()

    token = os.getenv("BOT_TOKEN", "").strip()
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    app_url = args.url.strip().rstrip("/")
    if not token or not secret or not app_url:
        raise SystemExit("BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET and APP_URL/--url are required")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", secret):
        raise SystemExit("TELEGRAM_WEBHOOK_SECRET must contain only A-Z, a-z, 0-9, _ and -")
    if not app_url.startswith("https://"):
        raise SystemExit("The deployed APP_URL must start with https://")

    webhook_url = f"{app_url}/api/telegram"
    telegram_call(
        token,
        "setWebhook",
        {
            "url": webhook_url,
            "secret_token": secret,
            "allowed_updates": ["message", "callback_query"],
        },
    )
    telegram_call(token, "setMyCommands", {"commands": COMMANDS})
    print(f"Telegram webhook configured: {webhook_url}")


if __name__ == "__main__":
    main()
