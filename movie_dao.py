from typing import Optional
from database import get_connection
from models import Movie

class MovieDAO:
    def getAll(self) -> list[Movie]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, duration, rating, status_id FROM movies ORDER BY id"
            ).fetchall()
        return [Movie(id=r["id"], title=r["title"], duration=r["duration"],
                      rating=r["rating"], status_id=r["status_id"]) for r in rows]

    def getById(self, movie_id: int) -> Optional[Movie]:
        with get_connection() as conn:
            r = conn.execute(
                "SELECT id, title, duration, rating, status_id FROM movies WHERE id = ?",
                (movie_id,)
            ).fetchone()
        if r is None:
            return None
        return Movie(id=r["id"], title=r["title"], duration=r["duration"],
                     rating=r["rating"], status_id=r["status_id"])

    def insert(self, movie: Movie) -> bool:
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO movies (title, duration, rating, status_id) VALUES (?, ?, ?, ?)",
                    (movie.title, movie.duration, movie.rating, movie.status_id)
                )
                movie.id = cursor.lastrowid
            return True
        except Exception as exc:
            print(f"Ошибка добавления фильма: {exc}")
            return False

    def update(self, movie: Movie) -> bool:
        if movie.id is None:
            return False
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    """UPDATE movies
                       SET title = ?, duration = ?, rating = ?, status_id = ?
                       WHERE id = ?""",
                    (movie.title, movie.duration, movie.rating, movie.status_id, movie.id)
                )
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Ошибка обновления фильма: {exc}")
            return False

    def delete(self, movie_id: int) -> bool:
        try:
            with get_connection() as conn:
                cursor = conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            return cursor.rowcount > 0
        except Exception as exc:
            print(f"Ошибка удаления фильма: {exc}")
            return False
