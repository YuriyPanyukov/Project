"""DAO: единственное место, где слой приложения выполняет SQL-запросы."""
class MovieDAO:
    def __init__(self, connection):
        self.connection = connection

    def getAll(self):
        return [dict(row) for row in self.connection.execute(
            "SELECT id, title, duration, rating, status_id FROM movies ORDER BY title"
        ).fetchall()]

    def getById(self, movie_id):
        row = self.connection.execute(
            "SELECT id, title, duration, rating, status_id FROM movies WHERE id = ?",
            (movie_id,)
        ).fetchone()
        return dict(row) if row else None

    def search_movies(self, query="", genre_id=None, status_id=None,
                      min_rating=None, max_rating=None, sort_by="title",
                      sort_order="ASC", descending=None):
        allowed = {"title", "duration", "rating"}
        if descending is not None:
            sort_order = "DESC" if descending else "ASC"
        sort_order = str(sort_order).upper()
        if sort_order not in {"ASC", "DESC"}:
            raise ValueError("Недопустимое направление сортировки.")
        if sort_by not in allowed:
            raise ValueError("Недопустимое поле сортировки.")
        sql = """SELECT DISTINCT m.id, m.title, m.duration, m.rating, m.status_id
                 FROM movies AS m"""
        params = []
        conditions = []
        if genre_id is not None:
            sql += " JOIN movie_genres AS mg ON mg.movie_id = m.id"
            conditions.append("mg.genre_id = ?")
            params.append(genre_id)
        if status_id is not None:
            conditions.append("m.status_id = ?")
            params.append(status_id)
        if min_rating is not None:
            conditions.append("m.rating >= ?")
            params.append(min_rating)
        if max_rating is not None:
            conditions.append("m.rating <= ?")
            params.append(max_rating)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY m." + sort_by + " " + sort_order
        rows = [dict(row) for row in self.connection.execute(sql, params).fetchall()]
        # Python casefold обеспечивает корректный поиск без учёта регистра для кириллицы.
        if query:
            query_folded = query.casefold()
            rows = [row for row in rows if query_folded in row["title"].casefold()]
        return rows

    def insert(self, movie):
        cursor = self.connection.execute(
            "INSERT INTO movies(title, duration, rating, status_id) VALUES (?, ?, ?, ?)",
            (movie["title"], movie["duration"], movie.get("rating"), movie["status_id"])
        )
        return cursor.lastrowid

    def update(self, movie):
        cursor = self.connection.execute(
            """UPDATE movies SET title = ?, duration = ?, rating = ?, status_id = ?
               WHERE id = ?""",
            (movie["title"], movie["duration"], movie.get("rating"),
             movie["status_id"], movie["id"])
        )
        return cursor.rowcount > 0

    def delete(self, movie_id):
        cursor = self.connection.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        return cursor.rowcount > 0


class StatsDAO:
    def __init__(self, connection):
        self.connection = connection

    def getCollectionSummaryStats(self):
        row = self.connection.execute("""
            SELECT COUNT(*) AS total_count, AVG(rating) AS average_rating
            FROM movies
        """).fetchone()
        return {"total_count": row["total_count"], "average_rating": row["average_rating"]}

    def getTopMoviePersonsByRole(self, role, limit):
        return [dict(row) for row in self.connection.execute("""
            SELECT p.full_name, COUNT(*) AS movie_count
            FROM movie_persons mp JOIN persons p ON p.id = mp.person_id
            WHERE mp.role = ?
            GROUP BY p.id, p.full_name
            ORDER BY movie_count DESC, p.full_name
            LIMIT ?
        """, (role, limit)).fetchall()]

    def getMoviesDistributionByStatus(self):
        return [dict(row) for row in self.connection.execute("""
            SELECT s.name AS status, COUNT(m.id) AS movie_count
            FROM statuses s LEFT JOIN movies m ON m.status_id = s.id
            GROUP BY s.id, s.name ORDER BY s.id
        """).fetchall()]

    def getTopGenresReport(self, limit):
        return [dict(row) for row in self.connection.execute("""
            SELECT g.name AS genre, COUNT(mg.movie_id) AS movie_count
            FROM genres g LEFT JOIN movie_genres mg ON mg.genre_id = g.id
            GROUP BY g.id, g.name
            ORDER BY movie_count DESC, g.name
            LIMIT ?
        """, (limit,)).fetchall()]

    def status_exists(self, status_id):
        row = self.connection.execute(
            "SELECT id FROM statuses WHERE id = ?", (status_id,)
        ).fetchone()
        return row is not None

    def find_status_id(self, status_name):
        row = self.connection.execute(
            "SELECT id FROM statuses WHERE name = ?", (status_name,)
        ).fetchone()
        return row["id"] if row else None

    def exists_ids(self, table, ids):
        """Проверяет существование набора ID; имя таблицы выбирается только из белого списка."""
        allowed = {"genres": "genres", "persons": "persons"}
        if table not in allowed:
            raise ValueError("Недопустимая таблица для проверки идентификаторов.")
        ids = list(dict.fromkeys(ids))
        if not ids:
            return True
        placeholders = ",".join("?" for _ in ids)
        rows = self.connection.execute(
            f"SELECT id FROM {allowed[table]} WHERE id IN ({placeholders})", ids
        ).fetchall()
        return len(rows) == len(ids)

    def replace_movie_links(self, movie_id, genre_ids=None, persons=None):
        """Заменяет связи фильма. Вызывать внутри транзакции."""
        if genre_ids is not None:
            self.connection.execute("DELETE FROM movie_genres WHERE movie_id = ?", (movie_id,))
            self.connection.executemany(
                "INSERT INTO movie_genres(movie_id, genre_id) VALUES (?, ?)",
                [(movie_id, gid) for gid in dict.fromkeys(genre_ids)]
            )
        if persons is not None:
            self.connection.execute("DELETE FROM movie_persons WHERE movie_id = ?", (movie_id,))
            self.connection.executemany(
                "INSERT INTO movie_persons(movie_id, person_id, role) VALUES (?, ?, ?)",
                [(movie_id, person_id, role) for person_id, role in persons]
            )

    def get_movie_links(self, movie_id):
        genres = [row["genre_id"] for row in self.connection.execute(
            "SELECT genre_id FROM movie_genres WHERE movie_id = ?", (movie_id,)
        )]
        persons = [(row["person_id"], row["role"]) for row in self.connection.execute(
            "SELECT person_id, role FROM movie_persons WHERE movie_id = ?", (movie_id,)
        )]
        return {"genre_ids": genres, "persons": persons}
