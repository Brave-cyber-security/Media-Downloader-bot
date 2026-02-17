from __future__ import annotations
import asyncio
import logging
import re
import shlex
import tempfile
import inspect
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
import aiohttp
from shazamio import Shazam
from app.core.extensions.utils import WORKDIR

logger = logging.getLogger(__name__)

MUSIC_DIR = WORKDIR.parent / "media" / "music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

# Reduced for faster response
MAX_RESULTS, CHUNK = 30, 10
FFMPEG_WAV = "-vn -acodec pcm_s16le -ac 1 -ar 16000 -t 10 -f wav"
TOKEN_RE = re.compile(r"\w+")

# Smaller cache for faster lookups
_text_search_cache: Dict[str, tuple] = {}  # (results, timestamp)
CACHE_MAX_SIZE = 30
CACHE_TTL = 180  # 3 minutes


async def _close_shazam_client(client: Shazam) -> None:
    close_method = getattr(client, "close", None)
    if not callable(close_method):
        return
    try:
        result = close_method()
        if inspect.isawaitable(result):
            await result
    except Exception:
        pass


def _score(hit: Dict, tokens: List[str]) -> float:
    """Faster scoring algorithm."""
    track = hit.get("track", hit)
    title = track.get("title", "").lower()
    artist = track.get("subtitle", "").lower()

    if not tokens:
        return 0

    score = 0
    query_text = " ".join(tokens)

    # Quick scoring
    if query_text in title:
        score += 10
    if query_text in artist:
        score += 5

    score += sum(1 for token in tokens if token in title or token in artist)
    return -score


async def find_music_by_text(text: str) -> List[Dict]:
    """Faster text search with caching."""
    if not text or len(text.strip()) < 2:
        return []

    text = text.strip()

    # Check cache with TTL
    if text in _text_search_cache:
        results, timestamp = _text_search_cache[text]
        if asyncio.get_event_loop().time() - timestamp < CACHE_TTL:
            return results

    try:
        shazam = Shazam()

        # Parallel search with smaller chunks
        tasks = []
        for offset in range(0, MAX_RESULTS, CHUNK):
            task = shazam.search_track(text, limit=CHUNK, offset=offset)
            tasks.append(task)

        # Faster timeout
        blocks = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True), timeout=8
        )

        hits: List[Dict] = []
        for block in blocks:
            if isinstance(block, dict) and "tracks" in block:
                hits.extend(block["tracks"].get("hits", []))

        # Quick scoring and sorting
        tokens = [t.lower() for t in TOKEN_RE.findall(text) if len(t) > 1]
        if tokens:
            hits.sort(key=lambda h: _score(h, tokens))

        result = hits[:MAX_RESULTS]

        # Update cache
        if len(_text_search_cache) >= CACHE_MAX_SIZE:
            oldest_key = min(
                _text_search_cache.keys(), key=lambda k: _text_search_cache[k][1]
            )
            del _text_search_cache[oldest_key]

        _text_search_cache[text] = (result, asyncio.get_event_loop().time())
        return result

    except asyncio.TimeoutError:
        logger.warning(f"Shazam timeout: {text}")
        return []
    except Exception as e:
        logger.error(f"Shazam error: {e}")
        return []
    finally:
        if "shazam" in locals():
            await _close_shazam_client(shazam)


async def recognise_music_from_audio(src_path: str) -> List[Dict]:
    """Faster audio recognition."""
    if not src_path or not Path(src_path).exists():
        return []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_wav = Path(temp_dir) / f"{uuid4()}.wav"
        shazam = Shazam()

        try:
            # Faster ffmpeg conversion
            cmd = f"ffmpeg -hide_banner -loglevel error -y -i {shlex.quote(src_path)} {FFMPEG_WAV} {shlex.quote(str(temp_wav))}"

            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Shorter timeout for conversion
            try:
                await asyncio.wait_for(process.communicate(), timeout=15)
            except asyncio.TimeoutError:
                process.terminate()
                return []

            if process.returncode != 0 or not temp_wav.exists():
                return []

            # Faster recognition timeout
            recognition_result = await asyncio.wait_for(
                shazam.recognize(str(temp_wav)), timeout=20
            )

            if not recognition_result:
                return []

            hits: List[Dict] = []

            if "track" in recognition_result:
                hits.append({"track": recognition_result["track"]})

            for match in recognition_result.get("matches", [])[:5]:  # Limit matches
                if "track" in match:
                    hits.append({"track": match["track"]})

            return hits[:MAX_RESULTS]

        except asyncio.TimeoutError:
            logger.warning("Recognition timeout")
            return []
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return []
        finally:
            await _close_shazam_client(shazam)


async def download_music(url: str, filename: Optional[str] = None) -> Optional[str]:
    """Faster download with optimizations."""
    if not url:
        return None

    filename = filename or f"{uuid4()}.m4a"
    file_path = MUSIC_DIR / filename

    try:
        # Faster timeout and connection settings
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)

        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector
        ) as session:
            async with session.get(url) as response:
                response.raise_for_status()

                # Larger chunks for faster download
                with open(file_path, "wb") as fp:
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(16384):
                        fp.write(chunk)
                        downloaded += len(chunk)

                        # Size limit
                        if downloaded > 40 * 1024 * 1024:  # 40MB
                            break

                if file_path.exists() and file_path.stat().st_size > 0:
                    return str(file_path)

    except Exception as e:
        logger.error(f"Download error: {e}")
        if file_path.exists():
            file_path.unlink(missing_ok=True)

    return None


def clear_text_search_cache() -> None:
    """Clear cache."""
    global _text_search_cache
    _text_search_cache.clear()
