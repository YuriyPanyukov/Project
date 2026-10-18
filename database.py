import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("movies.db")

def get_connection():
    """Открывает соединение с SQLite и включает проверку внешних ключей."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
