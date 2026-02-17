import os
import shutil
import uuid

import requests
import re
import json
from bs4 import BeautifulSoup


class PinterestDL:
    def scrape(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Step 1: Get HTML
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        # Step 2: Try to find video in <script> tag first (more reliable)
        video_url = None
        scripts = soup.find_all("script")

        for script in scripts:
            if script.string:
                # Look for video_list in script content
                if "video_list" in script.string:
                    # Try to extract video_list JSON
                    match = re.search(r'"video_list":\s*({[^}]+})', script.string)
                    if match:
                        try:
                            video_list_str = match.group(1)
                            video_list = json.loads(video_list_str)

                            # Pick highest quality available
                            if "V_720P" in video_list and video_list["V_720P"]:
                                video_url = video_list["V_720P"]["url"]
                            elif "V_480P" in video_list and video_list["V_480P"]:
                                video_url = video_list["V_480P"]["url"]
                            elif "V_360P" in video_list and video_list["V_360P"]:
                                video_url = video_list["V_360P"]["url"]

                            if video_url:
                                break
                        except Exception as e:
                            print(f"Error parsing video JSON: {e}")
                            continue

                # Alternative: look for direct video URLs in scripts
                if not video_url:
                    video_patterns = [
                        r'"url":\s*"([^"]*\.mp4[^"]*)"',
                        r'"videoUrl":\s*"([^"]*)"',
                        r'"src":\s*"([^"]*\.mp4[^"]*)"',
                    ]

                    for pattern in video_patterns:
                        matches = re.findall(pattern, script.string)
                        if matches:
                            video_url = matches[0]
                            break

                if video_url:
                    break

        # Step 3: Fallback to og:video meta tag
        if not video_url:
            video_tag = soup.find("meta", property="og:video")
            if video_tag and video_tag.get("content"):
                video_url = video_tag["content"]

        # Step 4: If we found a video URL, use it
        if video_url:
            # Clean up the URL (remove escape characters)
            video_url = video_url.replace("\\u0026", "&").replace("\\/", "/")

            # Verify it's actually a video by checking the response
            try:
                head_response = requests.head(video_url, headers=headers)
                content_type = head_response.headers.get("content-type", "").lower()

                if "video" in content_type or video_url.endswith(".mp4"):
                    media_url = video_url
                    media_type = "video"
                    extension = ".mp4"
                else:
                    # If it's not a video, fall back to image
                    raise ValueError("URL doesn't point to video content")

            except Exception as e:
                print(f"Video URL verification failed: {e}")
                video_url = None

        # Step 5: Fallback to image if no video found
        if not video_url:
            image_tag = soup.find("meta", property="og:image")
            if image_tag and image_tag.get("content"):
                media_url = image_tag["content"]
                media_type = "image"
                extension = ".jpg"
            else:
                raise ValueError("❌ Could not find media in Pinterest page")

        # Step 6: Download the media
        print(f"📥 Downloading {media_type} from: {media_url}")
        media_response = requests.get(media_url, headers=headers)

        if media_response.status_code != 200:
            raise ValueError(
                f"❌ Failed to download media: HTTP {media_response.status_code}"
            )

        return type(
            "ScrapedData",
            (object,),
            {
                "media_type": media_type,
                "extension": extension,
                "buffer": media_response.content,
                "url": media_url,
            },
        )()


class PinterestDownloader:
    def __init__(self):
        self.downloader = PinterestDL()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def download(self, url: str, out_path: str, filename: str) -> tuple[str, str]:
        """
        Downloads media from a given URL and saves it to a specified location with a specified filename.

        This method uses a downloader instance to scrape media from the provided URL. The resulting
        media is written to disk in the specified output path and filename. The media type and
        file extension are determined based on the scraper's result, and if not provided, defaults
        are applied. The function ensures the output path exists and writes the scraped media
        buffer to a file at the designated location.

        Parameters:
        url: str
            The URL from which to download the media.
        out_path: str
            The directory path where the media should be saved.
        filename: str
            The base filename to use when saving the file (without extension).

        Returns:
        tuple[str, str]
            A tuple consisting of the full path to the downloaded media and the media type.

        >>> Example:
        >>>    with PinterestDownloader() as downloader:
        >>>    a = downloader.download(
        >>>    url="https://pin.it/4OdmhuJ4a",
        >>>    out_path="./downloads",
        >>>    filename=uuid.uuid4().hex
        >>>)
        >>>print(a)
        """
        result = self.downloader.scrape(url)

        media_type = result.media_type or "unknown"
        ext = result.extension or (".mp4" if media_type == "video" else ".jpg")
        full_path = os.path.join(out_path, filename + ext)

        os.makedirs(out_path, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(result.buffer)

        print(f"✅ Downloaded {media_type} to {full_path}")
        return full_path, media_type

    def clear(self, path: str):
        if os.path.isdir(path):
            shutil.rmtree(path)
            os.makedirs(path)
            print(f"🧹 Cleared directory: {path}")
        else:
            print(f"⚠️ Not a valid directory: {path}")
