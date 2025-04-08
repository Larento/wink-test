from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, status

from wink_test.dependencies import (
    AppState,
    BalancerSettingsDbModelDependency,
    SettingsDependency,
    get_balancer_settings_db_model,
    get_db_connection,
)
from wink_test.settings import BalancerSettings, Settings


@asynccontextmanager
async def lifespan(app: FastAPI, settings: Settings, app_state: AppState):
    db_connection = get_db_connection(settings)
    if db_connection:
        async with db_connection.connect():
            model = get_balancer_settings_db_model(db_connection)
            assert model
            await model.create_table()
            existing_settings = await model.get_object()
            if not existing_settings:
                await model.create_object(settings)
            else:
                app_state.update_balancer_settings(existing_settings)
            yield
    else:
        yield


router = APIRouter(prefix="/settings")


@router.get("")
@router.get("/")
async def read_settings(settings: SettingsDependency):
    return BalancerSettings(cdn_host=settings.cdn_host, redirect_ratio=settings.redirect_ratio)


@router.put("")
@router.put("/")
async def update_settings(settings: BalancerSettings, balancer_settings_db_model: BalancerSettingsDbModelDependency):
    if not balancer_settings_db_model:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return await balancer_settings_db_model.update_object(settings)
