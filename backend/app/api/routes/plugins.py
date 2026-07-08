from fastapi import APIRouter

from app.schemas import PluginManifest
from app.services.plugin_manager import plugin_manager


router = APIRouter()


@router.get("/plugins", response_model=list[PluginManifest])
def list_plugins() -> list[PluginManifest]:
    return plugin_manager.discover()
