"""Создание соединения SQLite. Для каждого соединения включаются внешние ключи."""
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / "movies.db"

def get_connection(db_path=DEFAULT_DB):
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
