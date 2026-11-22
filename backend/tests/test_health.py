from fastapi.testclient import TestClient

from auris.api.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_settings_defaults(monkeypatch):
    from auris.core.config import Settings

    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    settings = Settings()
    assert settings.CELERY_BROKER_URL == "redis://localhost:6379/0"


def test_settings_read_from_env(auris_data_dir, monkeypatch):
    from auris.core.config import Settings

    monkeypatch.setenv("CELERY_BROKER_URL", "redis://redis:6379/1")
    settings = Settings()
    assert settings.AURIS_DATA_DIR == auris_data_dir
    assert settings.CELERY_BROKER_URL == "redis://redis:6379/1"
