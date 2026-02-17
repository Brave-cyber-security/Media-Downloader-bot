import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import time
import re
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ThreadsController:
    def __init__(self, download_path: Optional[Path] = None):
        self.download_path = download_path or Path.cwd().parent / "media" / "threads"
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.driver = None
        self._init_driver()

    def _init_driver(self):
        """Chrome driver sozlamalari"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            self.driver = webdriver.Chrome(
                service=Service("/usr/bin/chromedriver"), options=chrome_options
            )
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            logger.error(f"Chrome driver ishga tushirishda xatolik: {e}")
            raise

    async def download_file(self, url: str, filename: str) -> bool:
        """Fayl yuklab olish"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            filepath = self.download_path / filename
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"✓ Yuklandi: {filename}")
            return True
        except Exception as e:
            logger.error(f"✗ Xatolik: {filename} - {str(e)}")
            return False

    async def get_post_media(self, thread_url: str) -> List[Tuple[str, str]]:
        """Faqat asosiy post medialarini olish"""
        try:
            logger.info("Sahifa yuklanmoqda...")
            self.driver.get(thread_url)
            time.sleep(8)  # Sahifa to'liq yuklanishi uchun

            # Scroll qilish - ba'zida medialar lazy load bo'ladi
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight/2);"
            )
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            media_urls = []

            # Asosiy post containerini aniq topish
            logger.info("Asosiy post containerini qidiryapman...")

            # Threads sahifasidagi asosiy post strukturasini topish
            main_post_selectors = [
                # Threads-specific selectors
                '[data-testid="post-content"]',
                '[data-testid="post"]',
                '[role="article"]',
                "main article",
                'main div[role="article"]',
                # Carousel yoki media container
                '[data-testid="carousel"]',
                '[data-testid="media-container"]',
                # Umumiy post container
                'div[data-pressable-container="true"]',
            ]

            post_container = None
            for selector in main_post_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        post_container = elements[0]  # Birinchi element - asosiy post
                        logger.info(f"Post container topildi: {selector}")
                        break
                except:
                    continue

            if not post_container:
                logger.info("Post container topilmadi, barcha sahifani qidiryapman...")
                post_container = self.driver.find_element(By.TAG_NAME, "body")

            # Post container ichidagi medialarni qidirish
            logger.info("Post ichidagi medialarni qidiryapman...")

            # Avval videolarni topish
            videos = post_container.find_elements(By.TAG_NAME, "video")
            logger.info(f"Post ichida {len(videos)} ta video topildi")

            video_found = False
            for i, video in enumerate(videos):
                src = video.get_attribute("src")
                if src and self._is_main_post_media(src):
                    media_urls.append(("video", src))
                    video_found = True
                    logger.info(f"✓ Video {i + 1}: {src[:80]}...")
                else:
                    # Video source taglarini ham tekshirish
                    sources = video.find_elements(By.TAG_NAME, "source")
                    for j, source in enumerate(sources):
                        src = source.get_attribute("src")
                        if src and self._is_main_post_media(src):
                            media_urls.append(("video", src))
                            video_found = True
                            logger.info(
                                f"✓ Video source {i + 1}.{j + 1}: {src[:80]}..."
                            )

            # Rasmlar - faqat video topilmagan bo'lsa yoki video bilan birga albom bo'lsa
            images = post_container.find_elements(By.TAG_NAME, "img")
            logger.info(f"Post ichida {len(images)} ta img topildi")

            for i, img in enumerate(images):
                src = img.get_attribute("src")
                if src and self._is_main_post_media(src):
                    # Agar video topilgan bo'lsa va bu video thumbnail bo'lsa, tashlab yuborish
                    if video_found and self._is_video_thumbnail(img):
                        logger.info(
                            f"✗ Rasm {i + 1} video thumbnail, tashlab yuborildi: {src[:80]}..."
                        )
                        continue

                    media_urls.append(("image", src))
                    logger.info(f"✓ Rasm {i + 1}: {src[:80]}...")
                else:
                    logger.info(
                        f"✗ Rasm {i + 1} rad qilindi: {src[:80] if src else 'src mavjud emas'}..."
                    )

            # Takroriy URLlarni olib tashlash
            unique_urls = []
            seen_urls = set()
            for media_type, url in media_urls:
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_urls.append((media_type, url))

            return unique_urls

        except Exception as e:
            logger.error(f"Xatolik: {str(e)}")
            return []

    def _is_video_thumbnail(self, img_element) -> bool:
        """Video thumbnail ekanligini tekshirish"""
        try:
            # Video element bilan bir xil container ichida ekanligini tekshirish
            parent = img_element.find_element(By.XPATH, "..")
            video_in_parent = parent.find_elements(By.TAG_NAME, "video")

            # Agar parent elementda video mavjud bo'lsa, bu thumbnail bo'lishi mumkin
            if video_in_parent:
                return True

            # Img elementining atributlarini tekshirish
            src = img_element.get_attribute("src")
            if src:
                # Video thumbnail pattern'lari
                thumbnail_patterns = [
                    "thumbnail",
                    "thumb",
                    "preview",
                    "poster",
                    "_t.",
                    "_thumb.",
                    "_preview.",
                ]

                for pattern in thumbnail_patterns:
                    if pattern in src.lower():
                        return True

            # CSS class yoki style atributlarini tekshirish
            classes = img_element.get_attribute("class") or ""
            if "thumbnail" in classes.lower() or "poster" in classes.lower():
                return True

            return False

        except:
            return False

    def _is_main_post_media(self, url: str) -> bool:
        """Asosiy post mediyasi ekanligini tekshirish"""
        if not url or not url.startswith("http"):
            return False

        url_lower = url.lower()

        # Profile rasmlari va kichik ikonalarni rad qilish
        excluded_patterns = [
            # Profil rasmlari
            "profile",
            "avatar",
            "pp_",
            "user_",
            # Kichik o'lchamlar
            "/40x40/",
            "/60x60/",
            "/80x80/",
            "/100x100/",
            "/150x150/",
            "s40x40",
            "s60x60",
            "s80x80",
            "s100x100",
            "s150x150",
            # Thumbnails
            "thumbnail",
            "thumb",
            "_t.",
            "_s.",
            # Ikonlar
            "icon",
            "logo",
            "badge",
            "emoji",
            # Boshqa keraksiz elementlar
            "loading",
            "placeholder",
            "blank",
        ]

        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        # Meta/Instagram CDN domainlarini tekshirish
        valid_domains = [
            "scontent",
            "cdninstagram",
            "instagram",
            "fbcdn",
            "xx.fbcdn.net",
            "scontent-",
        ]

        if not any(domain in url for domain in valid_domains):
            return False

        # Media fayl formatlarini tekshirish
        media_indicators = [
            # Rasm formatlar
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            # Video formatlar
            ".mp4",
            ".mov",
            ".webm",
            ".avi",
            # Instagram/Meta parametrlari
            "_nc_cat",
            "_nc_ohc",
            "_nc_ht",
            "ig_cache_key",
            # Media o'lchamlari (katta rasmlar)
            "1080x1080",
            "1080x1350",
            "1350x1080",
            "1440x1800",
            # High quality indicators
            "_n.jpg",
            "_n.mp4",
            "_n.webp",
        ]

        has_media_indicator = any(
            indicator in url_lower for indicator in media_indicators
        )

        # URL uzunligi bo'yicha ham tekshirish (odatda katta media fayllari uzunroq URLga ega)
        is_long_url = len(url) > 150

        return has_media_indicator and is_long_url

    async def download_media(self, thread_url: str) -> dict:
        """Thread'dan media fayllarni yuklab olish"""
        logger.info(f"Thread tahlil qilinmoqda: {thread_url}")

        try:
            media_urls = await self.get_post_media(thread_url)

            if not media_urls:
                return {
                    "success": False,
                    "message": "❌ Post ichida media fayllar topilmadi!",
                    "downloaded_files": [],
                }

            logger.info(f"✅ {len(media_urls)} ta media fayl topildi")

            downloaded_files = []
            failed_files = []

            for i, (media_type, url) in enumerate(media_urls, 1):
                # Fayl nomini yaratish
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)

                if not filename or "." not in filename:
                    ext = ".mp4" if media_type == "video" else ".jpg"
                    filename = f"{media_type}_{i}{ext}"

                # Fayl nomini tozalash
                filename = "".join(c for c in filename if c.isalnum() or c in "._-")

                # Agar fayl nomi bo'sh bo'lsa
                if not filename:
                    ext = ".mp4" if media_type == "video" else ".jpg"
                    filename = f"{media_type}_{i}{ext}"

                logger.info(f"📥 Yuklanmoqda ({i}/{len(media_urls)}): {filename}")
                success = await self.download_file(url, filename)

                if success:
                    downloaded_files.append(
                        {
                            "filename": filename,
                            "type": media_type,
                            "path": str(self.download_path / filename),
                        }
                    )
                else:
                    failed_files.append(
                        {"filename": filename, "type": media_type, "url": url}
                    )

            return {
                "success": True,
                "message": f"✅ {len(downloaded_files)} ta fayl yuklandi",
                "downloaded_files": downloaded_files,
                "failed_files": failed_files,
                "total_found": len(media_urls),
            }

        except Exception as e:
            logger.error(f"Download media xatolik: {e}")
            return {
                "success": False,
                "message": f"❌ Xatolik yuz berdi: {str(e)}",
                "downloaded_files": [],
            }

    def close(self):
        """Brauzer yopish"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        """Destructor"""
        self.close()
