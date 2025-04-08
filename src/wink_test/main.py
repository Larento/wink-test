from fastapi import FastAPI, Response, status
from fastapi.concurrency import asynccontextmanager

from wink_test.dependencies import get_settings
from wink_test.routers import balancer_api

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings:
        raise ValueError("Сервису не были предоставлены необходимые настройки, запуск невозможен.")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check():
    return Response(status_code=status.HTTP_200_OK)


app.include_router(balancer_api.router)
