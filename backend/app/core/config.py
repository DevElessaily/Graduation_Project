from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    ML_MODEL_DIR: str = "ml_models"

settings = Settings()