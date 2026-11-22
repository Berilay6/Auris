import pytest

from auris.core.config import get_settings


@pytest.fixture
def auris_data_dir(tmp_path, monkeypatch):
    """Her test için geçici bir `auris-data` klasörü verir ve ayarları buna yönlendirir."""
    data_dir = tmp_path / "auris-data"
    data_dir.mkdir()
    monkeypatch.setenv("AURIS_DATA_DIR", str(data_dir))
    get_settings.cache_clear()
    yield data_dir
    get_settings.cache_clear()
