from fastapi import FastAPI

from api.app.routes import ingest_router, health_router

app = FastAPI(title="Local Semantic Memory API")

app.include_router(ingest_router)
app.include_router(health_router)

@app.get("/")
def root():
    return {"status": "ok"}
