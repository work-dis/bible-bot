import runpy
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "configure_qstash.py"


def test_schedule_destination_keeps_https_scheme_visible() -> None:
    schedule_api_url = runpy.run_path(str(SCRIPT))["schedule_api_url"]

    result = schedule_api_url("https://bible-bot-five.vercel.app/api/cron")

    assert result == (
        "https://qstash.upstash.io/v2/schedules/https://bible-bot-five.vercel.app/api/cron"
    )
    assert "https%3A" not in result
