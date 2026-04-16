from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    REDIS_URL: str
    REDIS_TOKEN: str
    HF_TOKEN: str
    model_config = SettingsConfigDict(env_file=".env")
    
settings = Settings()