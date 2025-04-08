from fastapi import FastAPI, Response, status
from fastapi.concurrency import asynccontextmanager

from wink_test.dependencies import get_app_state, get_settings
from wink_test.routers import balancer_api, balancer_settings_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = await get_settings()
    app_state = get_app_state()
    async with balancer_api.lifespan(app, settings):
        async with balancer_settings_api.lifespan(app, settings, app_state):
            yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check():
    return Response(status_code=status.HTTP_200_OK)


app.include_router(balancer_api.router)
app.include_router(balancer_settings_api.router)
