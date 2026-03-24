from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://irms_user:irms_password@localhost:5432/irms_db"
    APP_NAME: str = "IRMS - Intelligent Restaurant Management System"

    model_config = {"env_file": ".env"}


settings = Settings()
