import logging
from pathlib import Path
from pytubefix import YouTube

logger = logging.getLogger(__name__)


class YouTubeShortsController:
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    async def download_video(self, url: str) -> str:
        try:
            yt = YouTube(url)

            # Eng yaxshi sifatli stream ni olish
            stream = (
                yt.streams.filter(progressive=True, file_extension="mp4")
                .order_by("resolution")
                .desc()
                .first()
            )

            if not stream:
                # Agar progressive topilmasa, adaptive stream dan foydalanish
                stream = (
                    yt.streams.filter(
                        adaptive=True, file_extension="mp4", only_video=True
                    )
                    .order_by("resolution")
                    .desc()
                    .first()
                )

            if not stream:
                raise ValueError("Yuklab olinadigan video topilmadi")

            filename = f"{yt.video_id}.mp4"
            filepath = self.save_dir / filename

            # Fayl mavjud bo'lsa qaytadan yuklamaslik
            if filepath.exists():
                return str(filepath)

            stream.download(output_path=str(self.save_dir), filename=filename)
            return str(filepath)

        except Exception as e:
            logger.exception(f"YouTube Shorts yuklab olishda xatolik: {url}")
            raise e
