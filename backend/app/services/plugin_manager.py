import json
from pathlib import Path

from app.core.config import get_settings
from app.schemas import PluginManifest


class PluginManager:
    def __init__(self, plugin_dir: Path | None = None) -> None:
        self.settings = get_settings()
        self.plugin_dir = plugin_dir or self.settings.plugin_dir

    def discover(self) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        if not self.plugin_dir.exists():
            return manifests
        for manifest_path in sorted(self.plugin_dir.glob("*/manifest.json")):
            with manifest_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            manifests.append(PluginManifest(**data))
        return manifests

    def select_for_intent(self, intent: str) -> list[PluginManifest]:
        manifests = self.discover()
        categories_by_intent = {
            "zip_count": {"disk", "metadata", "hash"},
            "filesystem": {"disk", "metadata", "hash"},
            "deleted_files": {"disk", "timeline"},
            "mac_time": {"disk", "timeline", "metadata"},
            "user_profile": {"disk", "registry", "browser", "timeline", "metadata"},
            "timeline": {"timeline", "disk", "registry", "browser"},
            "registry": {"registry"},
            "browser": {"browser"},
            "memory": {"memory"},
            "password": {"password", "disk"},
            "ioc": {"disk", "memory", "browser", "registry"},
        }
        wanted = categories_by_intent.get(intent, {"disk", "metadata", "report"})
        return [manifest for manifest in manifests if manifest.enabled and manifest.category in wanted]


plugin_manager = PluginManager()
