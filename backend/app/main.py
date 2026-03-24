from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import engine, Base
from app.routers import tables, menu, orders, inventory, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.include_router(tables.router, prefix="/api")
app.include_router(menu.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
