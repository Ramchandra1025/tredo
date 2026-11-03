import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    DATABASE = BASE_DIR / "database" / "trado.db"
    FRONTEND_DIR = BASE_DIR.parent / "frontend"
