import runpy
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "broadcast_update.py"


def test_update_broadcast_is_short_and_prompts_start() -> None:
    namespace = runpy.run_path(str(SCRIPT))
    text = namespace["UPDATE_TEXT"]

    assert "Бот обновился" in text
    assert "ежедневную главу" in text
    assert "сохранять главы" in text
    assert "отзывы и предложения" in text
    assert "/start" in text
    assert len(text) < 1000
