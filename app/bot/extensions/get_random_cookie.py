from app.core.extensions.utils import WORKDIR
from itertools import cycle
import os

COOKIE_CYCLES = {}


def get_random_cookie_for_instagram(_cookie_type: str) -> str | None:
    cookies_path = WORKDIR.parent / "static" / "cookie" / _cookie_type
    if _cookie_type not in COOKIE_CYCLES:
        if not cookies_path.exists():
            return None
        items = os.listdir(cookies_path)
        if not items:
            return None
        items.sort()
        COOKIE_CYCLES[_cookie_type] = cycle(items)

    return next(COOKIE_CYCLES[_cookie_type])


COOKIE_CYCLES_YOUTUBE = {}


def get_random_cookie_for_youtube(_cookie_type: str) -> str | None:
    cookies_path = WORKDIR.parent / "static" / "cookie" / _cookie_type
    if _cookie_type not in COOKIE_CYCLES_YOUTUBE:
        if not cookies_path.exists():
            return None
        items = os.listdir(cookies_path)
        if not items:
            return None
        items.sort()
        COOKIE_CYCLES_YOUTUBE[_cookie_type] = cycle(items)

    return next(COOKIE_CYCLES_YOUTUBE[_cookie_type])


def get_all_youtube_cookies(_cookie_type: str) -> list[str]:
    cookies_path = WORKDIR.parent / "static" / "cookie" / _cookie_type
    if not cookies_path.exists():
        return []
    return sorted(
        str(cookies_path / item)
        for item in os.listdir(cookies_path)
        if item.endswith(".txt")
    )
