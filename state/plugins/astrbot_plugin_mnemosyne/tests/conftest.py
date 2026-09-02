from __future__ import annotations

import sys
import types
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_ROOT = PLUGIN_ROOT.parent

for path in (PLUGIN_ROOT, PLUGINS_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _ensure_astrbot_test_stubs() -> None:
    try:
        import astrbot.api.star  # noqa: F401
        import astrbot.core.log  # noqa: F401
        return
    except ImportError:
        pass

    astrbot = sys.modules.get("astrbot") or types.ModuleType("astrbot")
    astrbot_api = sys.modules.get("astrbot.api") or types.ModuleType("astrbot.api")
    astrbot_api_event = sys.modules.get("astrbot.api.event") or types.ModuleType(
        "astrbot.api.event"
    )
    astrbot_api_provider = sys.modules.get("astrbot.api.provider") or types.ModuleType(
        "astrbot.api.provider"
    )
    astrbot_api_star = sys.modules.get("astrbot.api.star") or types.ModuleType(
        "astrbot.api.star"
    )
    astrbot_core = sys.modules.get("astrbot.core") or types.ModuleType("astrbot.core")
    astrbot_core_log = sys.modules.get("astrbot.core.log") or types.ModuleType(
        "astrbot.core.log"
    )

    class _Logger:
        def debug(self, *_args, **_kwargs):
            return None

        def info(self, *_args, **_kwargs):
            return None

        def warning(self, *_args, **_kwargs):
            return None

        def error(self, *_args, **_kwargs):
            return None

    class _LogManager:
        @staticmethod
        def GetLogger(*_args, **_kwargs):
            return _Logger()

    class _AstrMessageEvent:
        pass

    class _ProviderRequest:
        pass

    class _LLMResponse:
        pass

    class _StarTools:
        pass

    astrbot_api.logger = getattr(astrbot_api, "logger", _Logger())
    astrbot_api_event.AstrMessageEvent = getattr(
        astrbot_api_event, "AstrMessageEvent", _AstrMessageEvent
    )
    astrbot_api_provider.ProviderRequest = getattr(
        astrbot_api_provider, "ProviderRequest", _ProviderRequest
    )
    astrbot_api_provider.LLMResponse = getattr(
        astrbot_api_provider, "LLMResponse", _LLMResponse
    )
    astrbot_api_star.StarTools = getattr(astrbot_api_star, "StarTools", _StarTools)
    astrbot_core_log.LogManager = getattr(astrbot_core_log, "LogManager", _LogManager)

    astrbot.api = astrbot_api
    astrbot.core = astrbot_core
    astrbot_api.event = astrbot_api_event
    astrbot_api.provider = astrbot_api_provider
    astrbot_api.star = astrbot_api_star
    astrbot_core.log = astrbot_core_log

    sys.modules["astrbot"] = astrbot
    sys.modules["astrbot.api"] = astrbot_api
    sys.modules["astrbot.api.event"] = astrbot_api_event
    sys.modules["astrbot.api.provider"] = astrbot_api_provider
    sys.modules["astrbot.api.star"] = astrbot_api_star
    sys.modules["astrbot.core"] = astrbot_core
    sys.modules["astrbot.core.log"] = astrbot_core_log


_ensure_astrbot_test_stubs()
