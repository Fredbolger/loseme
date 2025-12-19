from fastapi import FastAPI

app = FastAPI(title="Semantic Memory API")

@app.get("/health")
def health():
    return {"status": "ok"}

