from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional
from app.bot.handlers.youtube_search import youtube_search
from app.bot.handlers.youtube_handler import (
    download_music_from_youtube,
    download_video_from_youtube,
    cleanup_old_files,
)

logger = logging.getLogger(__name__)


class ShazamController:
    def __init__(self) -> None:
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_loop()

    def _start_cleanup_loop(self) -> None:
        """Start optimized cleanup loop."""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def search(self, query: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Faster search with reduced timeout."""
        if not query or len(query.strip()) < 2:
            return []

        try:
            return await asyncio.wait_for(
                youtube_search(query.strip(), min(limit, 50)),
                timeout=6,  # Reduced timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Search timeout: {query}")
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def download_full_track(self, title: str, artist: str) -> Optional[str]:
        """Faster track download."""
        if not title or not artist:
            return None

        try:
            return await asyncio.wait_for(
                download_music_from_youtube(title.strip(), artist.strip()),
                timeout=50,  # Reduced timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Download timeout: {title}")
            return None
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None

    async def download_video(self, video_id: str, title: str) -> Optional[str]:
        """Faster video download."""
        if not video_id or not title:
            return None

        try:
            return await asyncio.wait_for(
                download_video_from_youtube(video_id.strip(), title.strip()),
                timeout=70,  # Reduced timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Video timeout: {video_id}")
            return None
        except Exception as e:
            logger.error(f"Video error: {e}")
            return None

    @staticmethod
    def ytdict_to_info(data: Dict[str, Any]) -> Dict[str, str]:
        """Fast conversion with validation."""
        return {
            "title": str(data.get("title", "Unknown")).strip(),
            "artist": str(data.get("artist", "Unknown")).strip(),
        }

    async def _cleanup_loop(self) -> None:
        """Optimized cleanup loop."""
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutes instead of 1 hour
                await cleanup_old_files()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def shutdown(self) -> None:
        """Fast shutdown."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
