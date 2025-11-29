import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')

if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY not found in .env file")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

if not POSTGRES_USER:
    raise ValueError("POSTGRES_USER not found in .env file")

if not POSTGRES_PASSWORD:
    raise ValueError("POSTGRES_PASSWORD not found in .env file")

if not POSTGRES_DB:
    raise ValueError("POSTGRES_DB not found in .env file")