FROM python:3.12-slim

WORKDIR /app

# ───── Zarur kutubxonalarni o‘rnatish ─────
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    unzip \
    wget \
    gnupg \
    ffmpeg \
    libnss3 libxss1 libasound2 libxshmfence1 \
    libatk-bridge2.0-0 libgtk-3-0 libgbm1 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# ───── Chromium va ChromeDriver o‘rnatish ─────
RUN apt-get update && apt-get install -y chromium chromium-driver

# ───── Python requirements ─────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ───── Copy loyihani va start fayllar ─────
COPY . .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8443 443 80
