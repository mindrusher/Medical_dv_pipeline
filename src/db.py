# ДБ коннектор

import os
import psycopg2

from pathlib import Path
from dotenv import load_dotenv

from psycopg2.extensions import connection


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    BASE_DIR / ".env"
)


def get_connection() -> connection:
    """
        Создает подключение к PostgreSQL.
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
