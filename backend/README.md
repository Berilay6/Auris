# Auris Backend

## Testler nasıl çalışır

Bağımlılıkları kurduktan sonra `backend/` klasöründe `pytest` ile testleri, `ruff check .` ile kod biçimi kontrolünü çalıştır. Testler geçici bir `auris-data` klasörü kullanır (`tests/conftest.py`), gerçek veri klasörüne dokunmaz. Ayarlar `pyproject.toml` içindeki `[tool.pytest.ini_options]` ve `[tool.ruff]` bölümlerinden okunur.
