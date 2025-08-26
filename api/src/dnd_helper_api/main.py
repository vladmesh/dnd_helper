from fastapi import FastAPI
from sqlmodel import SQLModel
from dnd_helper_api.db import engine
from dnd_helper_api.routers.users import router as users_router


app = FastAPI(title="DnD Helper API")


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


 


@app.on_event("startup")
def on_startup() -> None:
    # Ensure all SQLModel tables are created
    SQLModel.metadata.create_all(engine)

app.include_router(users_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dnd_helper_api.main:app", host="0.0.0.0", port=8000)
