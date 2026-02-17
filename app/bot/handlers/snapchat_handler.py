import logging
from app.core.extensions.utils import WORKDIR
from app.bot.controller.snapchat_controller import SnapchatController

logger = logging.getLogger(__name__)


async def download_snapchat_media(url: str) -> str | None:
    try:
        controller = SnapchatController()
        file_path = controller.download_snapchat_video(
            url, WORKDIR.parent / "media" / "snapchat"
        )
        return file_path
    except Exception as e:
        logger.error(f"Snapchat handler error: {e}")
        return None
