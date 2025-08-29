import os

from fastapi import FastAPI

from dnd_helper_api.logging_config import configure_logging
from dnd_helper_api.routers.monsters import router as monsters_router
from dnd_helper_api.routers.spells import router as spells_router
from dnd_helper_api.routers.users import router as users_router

configure_logging(
    service_name=os.getenv("LOG_SERVICE_NAME", "api"),
)

app = FastAPI(title="DnD Helper API")


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


 


app.include_router(users_router)
app.include_router(monsters_router)
app.include_router(spells_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dnd_helper_api.main:app", host="0.0.0.0", port=8000, log_config=None)
