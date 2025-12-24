import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('DB_HOST')
WEBSUB_CALLBACK_URL = os.getenv('WEBSUB_CALLBACK_URL')
WEBSUB_SECRET = os.getenv('WEBSUB_SECRET')
CHROME_EXTENSION_ID = os.getenv('PUBLIC_CHROME_EXTENSION_ID')

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}/{POSTGRES_DB}"

if not DB_HOST:
    raise ValueError("DB_HOST not found in .env file")

if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY not found in .env file")

if not FRONTEND_ORIGIN:
    raise ValueError("FRONTEND_ORIGIN not found in .env file")

if not POSTGRES_USER:
    raise ValueError("POSTGRES_USER not found in .env file")

if not POSTGRES_PASSWORD:
    raise ValueError("POSTGRES_PASSWORD not found in .env file")

if not POSTGRES_DB:
    raise ValueError("POSTGRES_DB not found in .env file")

if not WEBSUB_CALLBACK_URL:
    raise ValueError("WEBSUB_CALLBACK_URL not found in .env file")

if not WEBSUB_SECRET:
    raise ValueError("WEBSUB_SECRET not found in .env file")

if not CHROME_EXTENSION_ID:
    raise ValueError("CHROME_EXTENSION_ID not found in .env file")
