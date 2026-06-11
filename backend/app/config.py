from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Enterprise AI Ops Platform"
    environment: str = "development"
    debug: bool = True
    database_url: str
    anthropic_api_key: str
    secret_key: str
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()