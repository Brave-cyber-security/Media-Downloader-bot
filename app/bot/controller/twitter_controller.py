import os
import requests
import json
import logging
from pathlib import Path
from app.core.settings.config import Settings, get_settings

logger = logging.getLogger(__name__)
settings: Settings = get_settings()


class TwitterController:
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.api_url = "https://twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com/tweetgrab"
        self.headers = {
            "x-rapidapi-key": settings.TWITTER_API_KEY,
            "x-rapidapi-host": "twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com",
        }

    async def download_media(self, tweet_url: str) -> dict:
        try:
            response = requests.get(
                self.api_url, headers=self.headers, params={"url": tweet_url}
            )
            data = response.json()

            # API javobini batafsil logga yozish
            logger.info(f"=== TWITTER API JAVOBI ===")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

            # Xato tekshirish
            if response.status_code != 200:
                return {
                    "success": False,
                    "downloaded_files": [],
                    "message": f"❌ API xatosi: {response.status_code}",
                }

            if "error" in data:
                return {
                    "success": False,
                    "downloaded_files": [],
                    "message": f"❌ API xatosi: {data['error']}",
                }

            tweet_id = data.get("id", "unknown")
            download_paths = []

            # 1. media_list tekshirish
            if data.get("media_list"):
                logger.info(f"media_list topildi: {len(data['media_list'])} ta element")
                for i, media in enumerate(data["media_list"]):
                    logger.info(f"Media {i + 1}: {media}")

                    if media["type"] == "video":
                        # variants dan eng yaxshi video URL ni topish
                        video_url = self._get_best_video_url(media.get("variants", []))
                        if video_url:
                            logger.info(f"Eng yaxshi video URL: {video_url}")

                            filename = self.save_dir / f"video_{tweet_id}_{i + 1}.mp4"
                            success = self._download_video_safe(video_url, filename)
                            if success:
                                download_paths.append(
                                    {"type": "video", "path": str(filename)}
                                )
                        else:
                            logger.warning(f"Video URL topilmadi variants da: {media}")

            # 2. media.video tekshirish
            if data.get("media", {}).get("video") and not any(
                f["type"] == "video" for f in download_paths
            ):
                video_data = data["media"]["video"]
                logger.info(f"media.video topildi: {type(video_data)} - {video_data}")

                if isinstance(video_data, dict) and "variants" in video_data:
                    # variants dan eng yaxshi video URL ni topish
                    video_url = self._get_best_video_url(video_data["variants"])
                    if video_url:
                        logger.info(f"Eng yaxshi video URL: {video_url}")

                        filename = self.save_dir / f"video_{tweet_id}.mp4"
                        success = self._download_video_safe(video_url, filename)
                        if success:
                            download_paths.append(
                                {"type": "video", "path": str(filename)}
                            )

                elif isinstance(video_data, str):
                    # To'g'ridan-to'g'ri URL
                    video_info = self._check_video_url(video_data)
                    logger.info(f"Video URL info: {video_info}")

                    if video_info["valid"]:
                        filename = self.save_dir / f"video_{tweet_id}.mp4"
                        success = self._download_video_safe(video_data, filename)
                        if success:
                            download_paths.append(
                                {"type": "video", "path": str(filename)}
                            )

            # 3. Rasmlar
            if data.get("media", {}).get("photo"):
                for i, photo in enumerate(data["media"]["photo"]):
                    img_resp = requests.get(photo["url"], timeout=30)
                    filename = self.save_dir / f"photo_{tweet_id}_{i + 1}.jpg"
                    with open(filename, "wb") as f:
                        f.write(img_resp.content)
                    download_paths.append({"type": "image", "path": str(filename)})

            # Natija
            if not download_paths:
                return {
                    "success": False,
                    "downloaded_files": [],
                    "message": "❌ Hech qanday media topilmadi yoki yuklab olinmadi",
                }

            return {
                "success": True,
                "downloaded_files": download_paths,
                "message": "✅ Yuklab olish muvaffaqiyatli",
                "id": tweet_id,
            }

        except Exception as e:
            logger.exception("Twitter media yuklab olishda xatolik")
            return {
                "success": False,
                "downloaded_files": [],
                "message": f"❌ Yuklab olishda xatolik: {e}",
            }

    def _get_best_video_url(self, variants: list) -> str:
        """Eng yaxshi video URL ni topish"""
        if not variants:
            return None

        # Faqat mp4 formatdagi videolarni filtrlash
        mp4_variants = [
            v
            for v in variants
            if v.get("content_type") == "video/mp4" or v.get("type") == "video/mp4"
        ]

        if not mp4_variants:
            logger.warning("MP4 format topilmadi")
            return None

        # Eng yuqori bitrate bilan video ni tanlash
        best_variant = max(mp4_variants, key=lambda x: x.get("bitrate", 0))

        # URL ni topish
        video_url = best_variant.get("url") or best_variant.get("src")

        logger.info(
            f"Tanlangan variant: bitrate={best_variant.get('bitrate')}, url={video_url}"
        )
        return video_url

    def _check_video_url(self, video_url: str) -> dict:
        """Video URL ni tekshirish"""
        try:
            response = requests.head(video_url, timeout=10)
            content_type = response.headers.get("content-type", "")
            content_length = response.headers.get("content-length", "0")

            return {
                "valid": response.status_code == 200,
                "status_code": response.status_code,
                "content_type": content_type,
                "content_length": content_length,
                "is_video": "video" in content_type.lower(),
            }
        except Exception as e:
            logger.error(f"Video URL tekshirishda xatolik: {e}")
            return {"valid": False, "error": str(e)}

    def _download_video_safe(self, video_url: str, filename: Path) -> bool:
        """Video faylini xavfsiz yuklab olish"""
        try:
            logger.info(f"Video yuklab olish boshlandi: {video_url}")

            with requests.get(video_url, stream=True, timeout=60) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                logger.info(f"Content-Type: {content_type}")

                # Video formatini tekshirish
                if "video" not in content_type.lower() and not video_url.endswith(
                    ".mp4"
                ):
                    logger.warning(f"Bu video fayl emas: {content_type}")
                    return False

                total_size = int(response.headers.get("content-length", 0))
                logger.info(f"Fayl o'lchami: {total_size} bytes")

                # Fayl yuklab olish
                with open(filename, "wb") as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                file_size = filename.stat().st_size
                logger.info(f"Yuklangan fayl o'lchami: {file_size} bytes")

                # Fayl o'lchamini tekshirish
                if file_size == 0:
                    logger.error("Fayl bo'sh!")
                    filename.unlink(missing_ok=True)
                    return False

                # Minimum o'lcham tekshirish (1KB)
                if file_size < 1024:
                    logger.warning(f"Fayl juda kichik: {file_size} bytes")

                logger.info(f"Video muvaffaqiyatli yuklandi: {filename}")
                return True

        except Exception as e:
            logger.error(f"Video yuklab olishda xatolik: {e}")
            if filename.exists():
                filename.unlink(missing_ok=True)
            return False
