from app.bot.controller.pinterest_controller import PinterestDownloader
from uuid import uuid4

from app.core.extensions.utils import WORKDIR


async def download_pinterest_media(url: str) -> tuple[str, str] | None:
    """
    Downloads media from a Pinterest URL and saves it to a specified directory.

    This function utilizes the `PinterestDownloader` context manager to handle the download
    process. If the download is successful, it returns the path and filename of the downloaded
    media. In case of an error during the download, the function logs the error and returns None.
    The downloaded file is stored in a predefined directory under the 'media' folder with a
    randomly generated filename.

    Parameters:
        url: str
            The Pinterest media URL to be downloaded.

    Returns:
        tuple[str, str] | None
            A tuple containing the path and filename of the downloaded media, or None if the
            download fails.
    """
    with PinterestDownloader() as downloader:
        try:
            return downloader.download(
                url,
                out_path=WORKDIR.parent / "media" / "pinterest",
                filename=uuid4().hex,
            )
        except Exception as e:
            print(f"❌ Pinterest download error: {e}")
            return None
