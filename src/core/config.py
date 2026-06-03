from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "BotVK"
    DEBUG: bool = False
    SECRET_KEY: str

    DATABASE_URL: str = "sqlite:///./app.db"

    VK_GROUP_TOKEN: str = ""
    VK_GROUP_ID: int = 0
    VK_API_VERSION: str = "5.199"
    VK_CONFIRMATION_CODE: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    ENCRYPTION_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()