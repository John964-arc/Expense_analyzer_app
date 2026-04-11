import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


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

    # Supported currencies list
    SUPPORTED_CURRENCIES = [
        'INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'SGD',
        'JPY', 'CNY', 'AED', 'CHF', 'MYR', 'THB', 'NZD',
    ]


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DEV_DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'database', 'dev-data.sqlite')
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite://'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'database', 'data.sqlite')
    )


config = {
    'development': DevelopmentConfig,
    'testing':     TestingConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
