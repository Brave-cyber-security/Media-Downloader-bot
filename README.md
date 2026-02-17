# Aiogram Bot Template

This repository provides a minimal structure for creating Telegram bots with [Aiogram](https://docs.aiogram.dev/) and SQLAlchemy.  It includes basic database helpers and an example configuration file.

## Getting Started

1. **Create a virtual environment** and install the dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment variables.**  Copy `example.env` to `.env` and update the values inside.

3. **Run the bot**:

```bash
python app/server/server.py
```

## Docker Run

This project can run with Docker Compose and includes:
- PostgreSQL
- Selenium
- Local Telegram Bot API (`telegram-bot-api`) for large file workflows (up to 2GB in local mode)

Required `.env` variables for local Bot API:
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

Optional `.env` variable:
- `COOKIE_DIR` (default: `./static/cookie`)
  - If your cookies are under `app/static/cookie`, set `COOKIE_DIR=./app/static/cookie`.

Run:

```bash
docker compose up -d --build
```

## Project Structure

```plaintext
app/
├── bot/            # place handlers, routers and other bot modules here
├── core/           # settings and database helpers
│   ├── databases/
│   │   ├── postgres.py  # async PostgreSQL session
│   │   └── sqlite.py    # async SQLite session
│   └── settings/
│       └── config.py    # pydantic settings
└── server/
    └── server.py   # application entry point
migrations/         # Alembic migration scripts
entrypoint.sh       # helper script to start the bot
example.env         # template environment variables
requirements.txt    # project dependencies
```

### Database Connections
- **`postgres.py`** – creates an async SQLAlchemy engine for PostgreSQL.
- **`sqlite.py`** – creates an async SQLAlchemy engine for SQLite.

### Why this template?
This layout separates bot logic from configuration and database layers so you can quickly start building any type of bot.  The provided scripts give ready-made session factories and settings management using Pydantic.

## License
MIT
