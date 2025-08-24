from fastapi import FastAPI


app = FastAPI(title="DnD Helper API")


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


