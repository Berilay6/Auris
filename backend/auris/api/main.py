from fastapi import FastAPI

from auris import __version__
from auris.api.routes import health
from auris.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title="Auris API",
        version=__version__,
        description="Akıllı Trafik Akış Simülasyonu ve Yol Tasarım Karar Destek Sistemi",
    )
    app.include_router(health.router)
    return app


app = create_app()
