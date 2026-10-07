"""
Configuration module for DevTrackr API.

Centralized configuration management using environment variables.
"""

import os


class Config:
    """Application configuration class"""

    # API Configuration
    API_VERSION = "1.0.3"
    API_TITLE = "DevTrackr"
    API_DESCRIPTION = "A developer task tracking and time management API"

    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./devtrackr.db")

    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    ALLOWED_ORIGINS = [
        origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()
    ]

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Security Configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Feature Flags
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    ENABLE_TIME_TRACKING = os.getenv("ENABLE_TIME_TRACKING", "true").lower() == "true"

    # Rate Limiting (requests per minute)
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))

    @classmethod
    def get_cors_origins(cls) -> list[str]:
        """Get CORS origins, handling wildcard properly"""
        if cls.ALLOWED_ORIGINS == ["*"]:
            return ["*"]
        return cls.ALLOWED_ORIGINS

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL with fallback"""
        return cls.DATABASE_URL
