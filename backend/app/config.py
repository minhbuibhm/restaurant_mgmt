from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://irms_user:irms_password@localhost:5432/irms_db"
    APP_NAME: str = "IRMS - Intelligent Restaurant Management System"
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours

    model_config = {"env_file": ".env"}


settings = Settings()
