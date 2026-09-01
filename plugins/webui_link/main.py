import os

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


@register("webui_link", "mokingh", "DM the live WebUI tunnel link + creds", "1.0.0")
class WebUILink(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("webui")
    async def webui(self, event: AstrMessageEvent):
        root = os.environ.get("ASTRBOT_ROOT", os.getcwd())
        path = os.path.join(root, "data", "webui_url.txt")
        url = ""
        try:
            with open(path, encoding="utf-8") as f:
                url = f.read().strip()
        except Exception:
            url = ""

        if not url:
            yield event.plain_result(
                "No WebUI tunnel is live right now. "
                "Wait for the next shift boot — the bot DMs the fresh link to admins."
            )
            return

        pw = os.environ.get("DASH_PASSWORD", "")
        yield event.plain_result(
            f"🌩 AstrBot WebUI (current shift):\n{url}\n\nuser: admin\npass: {pw}\n\n"
            "Link rotates every ~5h shift."
        )
