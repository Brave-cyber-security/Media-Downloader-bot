import os


async def atomic_clear(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Failed to delete file {path}: {e}")
