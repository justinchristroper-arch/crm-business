from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', hide_input_in_errors=True)
    database_url: str
    migration_database_url: str = ''
    jwt_secret: str
    app_env: str = 'development'
    allowed_origins: list[str] = ['http://localhost:8000', 'http://127.0.0.1:8000']
    cookie_secure: bool = False
    demo_mode: bool = False
    enable_demo_reset: bool = False
    report_timezone: str = 'Asia/Jakarta'
    demo_password: str = 'PortfolioDemo!2026'

    @model_validator(mode='after')
    def secure_config(self):
        if len(self.jwt_secret) < 32 or self.jwt_secret.startswith('replace-'):
            raise ValueError('JWT_SECRET must be at least 32 random characters.')
        if not self.database_url.startswith(('postgresql://', 'postgresql+psycopg://')):
            raise ValueError('PostgreSQL is required. SQLite is not a production fallback.')
        if self.app_env == 'production':
            if not self.cookie_secure or not self.allowed_origins:
                raise ValueError('Production requires secure cookies and explicit origins.')
            if any(not o.startswith('https://') or '*' in o for o in self.allowed_origins):
                raise ValueError('Production origins must be exact HTTPS origins.')
        return self


@lru_cache
def settings():
    return Settings()
