import os
from datetime import timedelta
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *a, **k: None   # no‑op fallback

basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env.local if present
load_dotenv(os.path.join(basedir, '.env.local'))


class Config:
    SECRET_KEY                  = os.environ.get('SECRET_KEY') or 'super-secret-key-change-in-prod'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER               = os.path.join(basedir, 'static', 'uploads')
    ALLOWED_EXTENSIONS          = {'png', 'jpg', 'jpeg', 'gif'}
    PERMANENT_SESSION_LIFETIME  = timedelta(days=30)

    # Currency service — free tier of exchangerate-api.com (no key needed for v6 open)
    EXCHANGE_API_BASE           = 'https://open.er-api.com/v6/latest'
    EXCHANGE_CACHE_TTL_SECONDS  = 3600   # refresh rates every hour

    # PDF export – reportlab font
    PDF_FONT                    = 'Helvetica'

    # Default base currency for new users
    DEFAULT_CURRENCY            = 'INR'

    # Database engine options for stability on Render/Supabase
    # pool_pre_ping ensures stale connections are restarted
    # pool_recycle prevents connections from staying open too long
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # Supported currencies list
    SUPPORTED_CURRENCIES = [
        'INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'SGD',
        'JPY', 'CNY', 'AED', 'CHF', 'MYR', 'THB', 'NZD',
    ]


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        os.environ.get('DEV_DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'database', 'dev-data.sqlite')
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite://'


class ProductionConfig(Config):
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Render/Supabase compatibility: psycopg2 requires postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        # Enforce SSL for Supabase if not specified
        if "sslmode=" not in db_url:
            separator = "&" if "?" in db_url else "?"
            db_url += f"{separator}sslmode=require"
        
        # If using Supabase Transaction Pooler (port 6543), pgbouncer=true is recommended
        if ":6543" in db_url and "pgbouncer=" not in db_url:
            separator = "&" if "?" in db_url else "?"
            db_url += f"{separator}pgbouncer=true"
            
    SQLALCHEMY_DATABASE_URI = db_url or 'sqlite:///' + os.path.join(basedir, 'database', 'data.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing':     TestingConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
