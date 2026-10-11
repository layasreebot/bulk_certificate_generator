
from fastapi import FastAPI

from app.api.routes.jobs import router as jobs_router
from app.api.routes.certificates import router as certificates_router

app = FastAPI(
    title="Bulk Certificate Generator API",
    description="API for generating certificates in bulk.",
    version="1.0.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(jobs_router)
app.include_router(certificates_router)