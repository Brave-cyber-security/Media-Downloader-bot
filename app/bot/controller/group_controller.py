import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from app.bot.controller.tiktok_controller import TikTokDownloader
from app.bot.controller.pinterest_controller import PinterestDownloader
from app.bot.controller.threads_controller import ThreadsController
from app.bot.controller.twitter_controller import TwitterController
from app.bot.controller.like_controller import LikeeController
from app.bot.controller.shazam_controller import ShazamController
from app.bot.controller.snapchat_controller import SnapchatController
from app.bot.controller.shorts_controller import YouTubeShortsController
from app.bot.handlers.instagram_handler import download_instagram_video_only_mp4
from app.core.extensions.utils import WORKDIR
from app.core.settings.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PlatformType(Enum):
    TIKTOK = "tiktok"
    PINTEREST = "pinterest"
    THREADS = "threads"
    TWITTER = "twitter"
    LIKEE = "likee"
    SNAPCHAT = "snapchat"
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM = "instagram"


class GroupController:
    """Guruh uchun universal media downloader"""

    def __init__(self):
        self.media_dir = WORKDIR.parent / "media"
        self.platform_patterns = {
            PlatformType.TIKTOK: [
                r"(?:https?://)?(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com)",
                r"(?:https?://)?(?:www\.)?tiktok\.com/.*?/video/\d+",
                r"(?:https?://)?vm\.tiktok\.com/\w+",
            ],
            PlatformType.PINTEREST: [
                r"(?:https?://)?(?:www\.)?pinterest\.com",
                r"(?:https?://)?pin\.it",
            ],
            PlatformType.THREADS: [r"(?:https?://)?(?:www\.)?threads\.com"],
            PlatformType.TWITTER: [
                r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)",
                r"(?:https?://)?(?:mobile\.)?(?:twitter\.com|x\.com)",
            ],
            PlatformType.LIKEE: [
                r"(?:https?://)?(?:www\.)?likee\.video",
                r"(?:https?://)?l\.likee\.video",
            ],
            PlatformType.SNAPCHAT: [r"(?:https?://)?(?:www\.)?snapchat\.com"],
            PlatformType.YOUTUBE_SHORTS: [
                r"(?:https?://)?(?:www\.)?youtube\.com/shorts/",
                r"(?:https?://)?youtu\.be/.*(?:\?|&).*shorts",
            ],
            PlatformType.INSTAGRAM: [
                r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv)/"
            ],
        }

    def detect_platform(self, url: str) -> Optional[PlatformType]:
        """URL dan platformani aniqlash"""
        url = url.lower().strip()

        for platform, patterns in self.platform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform

        return None

    def is_social_media_link(self, text: str) -> bool:
        """Matnda social media link borligini tekshirish"""
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, text)

        for url in urls:
            if self.detect_platform(url):
                return True

        return False

    def extract_urls(self, text: str) -> list[str]:
        """Matndan URLlarni ajratib olish"""
        url_pattern = r"https?://[^\s]+"
        return re.findall(url_pattern, text)

    async def download_media(self, url: str) -> Dict[str, Any]:
        """URL dan media yuklab olish"""
        platform = self.detect_platform(url)

        if not platform:
            return {
                "success": False,
                "message": "❌ Qo'llab-quvvatlanmaydigan platform",
                "files": [],
            }

        try:
            if platform == PlatformType.TIKTOK:
                return await self._download_tiktok(url)
            elif platform == PlatformType.PINTEREST:
                return await self._download_pinterest(url)
            elif platform == PlatformType.THREADS:
                return await self._download_threads(url)
            elif platform == PlatformType.TWITTER:
                return await self._download_twitter(url)
            elif platform == PlatformType.LIKEE:
                return await self._download_likee(url)
            elif platform == PlatformType.SNAPCHAT:
                return await self._download_snapchat(url)
            elif platform == PlatformType.INSTAGRAM:
                return await self._download_instagram(url)
            elif platform == PlatformType.YOUTUBE_SHORTS:
                return await self._download_youtube_shorts(url)
            else:
                return {
                    "success": False,
                    "message": f"❌ {platform.value} hali qo'llab-quvvatlanmaydi",
                    "files": [],
                }

        except Exception as e:
            logger.error(f"Download error for {platform.value}: {e}")
            return {
                "success": False,
                "message": f"❌ Yuklab olishda xatolik: {str(e)}",
                "files": [],
            }

    async def _download_tiktok(self, url: str) -> Dict[str, Any]:
        """TikTok video yuklab olish"""
        save_path = self.media_dir / "tiktok"

        with TikTokDownloader() as downloader:
            file_path = downloader.download_video(url, str(save_path))

        if file_path and Path(file_path).exists():
            return {
                "success": True,
                "message": "✅ TikTok video yuklandi",
                "files": [{"type": "video", "path": file_path}],
            }

        return {"success": False, "message": "❌ TikTok video yuklanmadi", "files": []}

    async def _download_instagram(self, url: str) -> Dict[str, Any]:
        """Instagram video yuklab olish - Guruh uchun optimallashtirilgan"""
        try:
            from app.bot.handlers.instagram_handler import download_instagram_for_group

            return await download_instagram_for_group(url)
        except Exception as e:
            logger.error(f"Instagram download error: {e}")
            return {
                "success": False,
                "message": f"❌ Instagram xatolik: {str(e)[:100]}",
                "files": [],
            }

    async def _download_pinterest(self, url: str) -> Dict[str, Any]:
        """Pinterest media yuklab olish"""
        save_path = self.media_dir / "pinterest"

        with PinterestDownloader() as downloader:
            file_path, media_type = downloader.download(
                url, str(save_path), "pinterest_media"
            )

        if file_path and Path(file_path).exists():
            return {
                "success": True,
                "message": f"✅ Pinterest {media_type} yuklandi",
                "files": [{"type": media_type, "path": file_path}],
            }

        return {
            "success": False,
            "message": "❌ Pinterest media yuklanmadi",
            "files": [],
        }

    async def _download_threads(self, url: str) -> Dict[str, Any]:
        """Threads media yuklab olish"""
        controller = ThreadsController(self.media_dir / "threads")

        try:
            result = await controller.download_media(url)

            if result["success"] and result["downloaded_files"]:
                files = [
                    {"type": f["type"], "path": f["path"]}
                    for f in result["downloaded_files"]
                ]
                return {"success": True, "message": result["message"], "files": files}
        finally:
            controller.close()

        return {"success": False, "message": "❌ Threads media yuklanmadi", "files": []}

    async def _download_twitter(self, url: str) -> Dict[str, Any]:
        """Twitter media yuklab olish"""
        controller = TwitterController(self.media_dir / "twitter")
        result = await controller.download_media(url)

        if result["success"] and result["downloaded_files"]:
            files = [
                {"type": f["type"], "path": f["path"]}
                for f in result["downloaded_files"]
            ]
            return {"success": True, "message": result["message"], "files": files}

        return {"success": False, "message": "❌ Twitter media yuklanmadi", "files": []}

    async def _download_likee(self, url: str) -> Dict[str, Any]:
        """Likee video yuklab olish"""
        controller = LikeeController(settings.LIKEE_API_KEY)
        file_path = controller.download_video(url)

        if file_path and Path(file_path).exists():
            return {
                "success": True,
                "message": "✅ Likee video yuklandi",
                "files": [{"type": "video", "path": file_path}],
            }

        return {"success": False, "message": "❌ Likee video yuklanmadi", "files": []}

    async def _download_snapchat(self, url: str) -> Dict[str, Any]:
        """Snapchat video yuklab olish"""
        controller = SnapchatController()
        file_path = controller.download_snapchat_video(url, self.media_dir / "snapchat")

        if file_path and Path(file_path).exists():
            return {
                "success": True,
                "message": "✅ Snapchat video yuklandi",
                "files": [{"type": "video", "path": file_path}],
            }

        return {
            "success": False,
            "message": "❌ Snapchat video yuklanmadi",
            "files": [],
        }

    async def _download_youtube_shorts(self, url: str) -> Dict[str, Any]:
        """YouTube Shorts yuklab olish"""
        controller = YouTubeShortsController(self.media_dir / "youtube_shorts")

        try:
            file_path = await controller.download_video(url)

            if file_path and Path(file_path).exists():
                return {
                    "success": True,
                    "message": "✅ YouTube Shorts yuklandi",
                    "files": [{"type": "video", "path": file_path}],
                }
        except Exception as e:
            logger.error(f"YouTube Shorts download error: {e}")

        return {
            "success": False,
            "message": "❌ YouTube Shorts yuklanmadi",
            "files": [],
        }

    def get_supported_platforms(self) -> list[str]:
        """Qo'llab-quvvatlanadigan platformalar ro'yxati"""
        return [
            "TikTok",
            "Pinterest",
            "Threads",
            "Twitter/X",
            "Likee",
            "Snapchat",
            "YouTube Shorts",
            "Instagram",
        ]
