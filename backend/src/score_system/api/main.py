from fastapi import APIRouter, FastAPI

api_v1 = APIRouter(prefix="/api/v1")


@api_v1.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(title="Score System API", version="0.1.0")
app.include_router(api_v1)
