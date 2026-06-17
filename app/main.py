from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.exceptions import register_exception_handlers
from app.routers.catalog import router as catalog_router
from app.routers.customers import router as customers_router
from app.routers.orders import coupon_router, router as orders_router

app = FastAPI(title="BO Mangas API", version="1.0.0")
register_exception_handlers(app)
BASE_DIR = Path(__file__).resolve().parents[1]
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(catalog_router)
app.include_router(customers_router)
app.include_router(coupon_router)
app.include_router(orders_router)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
