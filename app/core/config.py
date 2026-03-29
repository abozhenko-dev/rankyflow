"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import json


class Settings(BaseSettings):
    # App
    app_name: str = "SEO Competitor Tracker"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/seo_tracker"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/seo_tracker"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str = "change-me-jwt"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # DataForSEO
    dataforseo_login: str = ""
    dataforseo_password: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Anthropic
    anthropic_api_key: str = ""

    # OpenAI (for GEO — ChatGPT tracking)
    openai_api_key: str = ""

    # Perplexity (for GEO — key platform with native citations)
    perplexity_api_key: str = ""

    # Google Gemini (for GEO)
    gemini_api_key: str = ""

    # DeepSeek (for GEO)
    deepseek_api_key: str = ""

    # Resend
    resend_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Sentry
    sentry_dsn: str = ""

    # CORS
    cors_origins: str = '["http://localhost:3000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
