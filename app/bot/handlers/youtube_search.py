from __future__ import annotations
import asyncio
import concurrent.futures
import logging
from typing import List, Dict
import yt_dlp
import os

logger = logging.getLogger(__name__)

# Optimized thread pool - increased workers for parallel processing
_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=min(8, (os.cpu_count() or 1) * 2), thread_name_prefix="yt-search"
)

# Smaller, faster cache with TTL
_search_cache: Dict[str, tuple] = {}  # (results, timestamp)
CACHE_MAX_SIZE = 50
CACHE_TTL = 300  # 5 minutes


def _search_sync(query: str, limit: int) -> List[Dict]:
    """Optimized YouTube search with faster options."""
    import time

    # Check cache with TTL
    cache_key = f"{query}:{limit}"
    if cache_key in _search_cache:
        results, timestamp = _search_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return results

    # Faster yt-dlp options
    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "default_search": f"ytsearch{limit}",
        "no_warnings": True,
        "ignoreerrors": True,
        "socket_timeout": 5,  # Faster timeout
        "retries": 1,  # Fewer retries
    }

    hits: List[Dict] = []
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(query, download=False)
            if data and "entries" in data:
                for entry in data["entries"][:limit]:  # Limit early
                    if entry:
                        hits.append(
                            {
                                "title": entry.get("title", "Unknown"),
                                "artist": entry.get("uploader", "Unknown"),
                                "duration": entry.get("duration") or 0,
                                "id": entry.get("id", ""),
                            }
                        )

        # Update cache with TTL
        if len(_search_cache) >= CACHE_MAX_SIZE:
            # Remove oldest entries
            oldest_key = min(_search_cache.keys(), key=lambda k: _search_cache[k][1])
            del _search_cache[oldest_key]

        _search_cache[cache_key] = (hits, time.time())

    except Exception as e:
        logger.error(f"YouTube search error: {e}")

    return hits


async def youtube_search(query: str, limit: int = 30) -> List[Dict]:
    """Faster async YouTube search."""
    if not query or len(query.strip()) < 2:
        return []

    # Reduced limit for faster results
    limit = min(limit, 50)

    loop = asyncio.get_running_loop()
    try:
        # Shorter timeout for faster response
        return await asyncio.wait_for(
            loop.run_in_executor(_pool, _search_sync, query.strip(), limit), timeout=8
        )
    except asyncio.TimeoutError:
        logger.warning(f"Search timeout: {query}")
        return []
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


def clear_search_cache() -> None:
    """Clear search cache."""
    global _search_cache
    _search_cache.clear()
