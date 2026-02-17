from functools import cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = "bot_token"

    ADMINS: str = "123456"
    USE_LOCAL_BOT_API: bool = False
    LOCAL_BOT_API_URL: str = "http://telegram-bot-api:8081"

    # POSTGRES CREDENTIALS
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DEBUG: bool = False

    # Selenium Credentials
    SELENIUM_REMOTE_URL: str

    # API KEYS
    LIKEE_API_KEY: str
    TWITTER_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def admins_list(self):
        admins = []
        for admin in self.ADMINS.split(","):
            admin = admin.strip()
            admins.append(int(admin))
        return admins

    def get_async_postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def get_sync_postgres_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@cache
def get_settings() -> Settings:
    return Settings()
