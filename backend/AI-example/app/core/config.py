from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./dev.db"

    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    GEMINI_API_KEY: str | None = None

    IMAGE_UPLOAD_DIR: str = "uploads/images"

    class Config:
        env_file = ".env"


settings = Settings()
