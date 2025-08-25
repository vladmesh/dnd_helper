from fastapi import FastAPI


app = FastAPI(title="DnD Helper API")


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dnd_helper_api.main:app", host="0.0.0.0", port=8000)
