from database import get_connection
from models import (
    CollectionSummaryDTO, PersonStatsDTO, StatusReportDTO, GenreReportDTO
)

class StatsDAO:
    def getCollectionSummaryStats(self) -> CollectionSummaryDTO:
        with get_connection() as conn:
            r = conn.execute("""
                SELECT COUNT(id) AS total_movies_count,
                       ROUND(AVG(rating), 2) AS average_collection_rating
                FROM movies
            """).fetchone()
        return CollectionSummaryDTO(
            total_movies_count=r["total_movies_count"],
            average_collection_rating=r["average_collection_rating"]
        )

    def getTopMoviePersonsByRole(self, roleName: str, limitSize: int) -> list[PersonStatsDTO]:
        if limitSize < 1:
            raise ValueError("limitSize должен быть положительным числом")
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT p.full_name AS person_name,
                       COUNT(mp.movie_id) AS movies_count,
                       ROUND(AVG(m.rating), 2) AS average_movies_rating
                FROM persons p
                JOIN movie_persons mp ON p.id = mp.person_id
                JOIN movies m ON mp.movie_id = m.id
                WHERE mp.role = ?
                GROUP BY p.id, p.full_name
                ORDER BY movies_count DESC, average_movies_rating DESC
                LIMIT ?
            """, (roleName, limitSize)).fetchall()
        return [PersonStatsDTO(r["person_name"], r["movies_count"],
                               r["average_movies_rating"]) for r in rows]

    def getMoviesDistributionByStatus(self) -> list[StatusReportDTO]:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT s.name AS status_name, COUNT(m.id) AS movies_count
                FROM statuses s
                LEFT JOIN movies m ON s.id = m.status_id
                GROUP BY s.id, s.name
                ORDER BY movies_count DESC, s.name ASC
            """).fetchall()
        return [StatusReportDTO(r["status_name"], r["movies_count"]) for r in rows]

    def getTopGenresReport(self) -> list[GenreReportDTO]:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT g.name AS genre_name,
                       COUNT(mg.movie_id) AS total_movies_in_genre
                FROM genres g
                JOIN movie_genres mg ON g.id = mg.genre_id
                GROUP BY g.id, g.name
                ORDER BY total_movies_in_genre DESC, g.name ASC
            """).fetchall()
        return [GenreReportDTO(r["genre_name"], r["total_movies_in_genre"]) for r in rows]
