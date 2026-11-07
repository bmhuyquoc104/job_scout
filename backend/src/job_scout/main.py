import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from job_scout.categories.router import router as categories_router
from job_scout.core.exception_handlers import register_exception_handlers
from job_scout.core.logging import configure_logging
from job_scout.database import engine
from job_scout.green_list.router import router as green_list_router
from job_scout.jobs.router import router as jobs_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield
    await engine.dispose()


app = FastAPI(title="Job Scout API", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(categories_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(green_list_router, prefix="/api")


def print_openapi() -> None:
    """Print the API schema; the frontend generates its types from it (`pnpm gen:api`)."""
    print(json.dumps(app.openapi()))


def run_dev_server() -> None:
    uvicorn.run("job_scout.main:app", reload=True)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
