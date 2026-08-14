import runpy
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "configure_telegram.py"


def test_admin_command_is_only_added_to_admin_scope() -> None:
    namespace = runpy.run_path(str(SCRIPT))
    commands = namespace["COMMANDS"]
    admin_commands = namespace["ADMIN_COMMANDS"]

    assert all(item["command"] != "reviews" for item in commands)
    assert any(item["command"] == "feedback" for item in commands)
    assert any(item["command"] == "reviews" for item in admin_commands)
