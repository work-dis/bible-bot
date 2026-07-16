from fastapi.testclient import TestClient

from bible_bot.vercel_app import _same_secret, app


def test_health_does_not_require_runtime_secrets(monkeypatch) -> None:
    for name in ("DATABASE_URL", "TELEGRAM_WEBHOOK_SECRET", "CRON_SECRET"):
        monkeypatch.delenv(name, raising=False)

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "bible-bot",
        "status": "ok",
        "database_configured": False,
        "webhook_configured": False,
        "delivery_configured": False,
    }


def test_cron_rejects_an_invalid_secret_before_initializing_runtime(monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "right-secret")

    response = TestClient(app).post("/api/cron", headers={"Authorization": "Bearer wrong-secret"})

    assert response.status_code == 401


def test_secret_comparison_requires_two_non_empty_values() -> None:
    assert _same_secret("same", "same") is True
    assert _same_secret("different", "same") is False
    assert _same_secret(None, "same") is False
    assert _same_secret("same", None) is False
