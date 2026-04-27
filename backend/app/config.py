from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./hcs_lld.db"
    IMPORT_TTL_MINUTES: int = 30
    APP_TIMEZONE: str = "Asia/Shanghai"
    BACKUP_DEFAULT_LOCAL_PATH: str = "./backups"
    BACKUP_SCHEDULER_INTERVAL_SECONDS: int = 60
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    BOOTSTRAP_ADMIN_USERNAME: str = "admin"
    BOOTSTRAP_ADMIN_PASSWORD: str = "admin"
    BOOTSTRAP_ADMIN_DISPLAY_NAME: str = "系统管理员"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
