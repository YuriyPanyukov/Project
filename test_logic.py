"""Консольные тесты бизнес-логики. Запуск: python -m unittest discover -s tests -v."""
import sqlite3
import unittest
from pathlib import Path

from dao import MovieDAO, StatsDAO
from services.movie_service import MovieService, BusinessRuleError, NotFoundError

ROOT = Path(__file__).resolve().parents[1]

class MovieServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript((ROOT / "init.sql").read_text(encoding="utf-8"))
        self.connection.execute("INSERT INTO genres(name) VALUES ('Фантастика')")
        self.connection.execute("INSERT INTO persons(full_name) VALUES ('Крис Нолан')")
        self.connection.commit()
        self.movie_dao = MovieDAO(self.connection)
        self.stats_dao = StatsDAO(self.connection)
        self.service = MovieService(self.movie_dao, self.stats_dao, self.connection)

    def tearDown(self):
        self.connection.close()

    def test_add_movie_success_and_links(self):
        movie = self.service.add_movie(" Интерстеллар ", 169, 8.6, 1, [1], [(1, "режиссёр")])
        self.assertEqual(movie["title"], "Интерстеллар")
        self.assertEqual(self.stats_dao.get_movie_links(movie["id"])["genre_ids"], [1])

    def test_add_movie_rejects_empty_title(self):
        with self.assertRaises(BusinessRuleError):
            self.service.add_movie("   ", 100)

    def test_add_movie_rejects_missing_genre_without_partial_insert(self):
        with self.assertRaises(BusinessRuleError):
            self.service.add_movie("Тест", 100, genre_ids=[999])
        self.assertEqual(len(self.movie_dao.getAll()), 0)

    def test_edit_movie_success(self):
        movie = self.service.add_movie("Фильм", 90, 7, 1)
        changed = self.service.edit_movie(movie["id"], "Новый фильм", 120, 8, 2)
        self.assertEqual(changed["title"], "Новый фильм")
        self.assertEqual(changed["status_id"], 2)

    def test_edit_only_changes_supplied_fields(self):
        movie = self.service.add_movie("Исходное название", 100, 7.5, 1)
        changed = self.service.edit_movie(movie["id"], title="Новое название")
        self.assertEqual(changed["title"], "Новое название")
        self.assertEqual(changed["duration"], 100)
        self.assertEqual(changed["rating"], 7.5)
        self.assertEqual(changed["status_id"], 1)

    def test_search_rejects_invalid_sort_order(self):
        with self.assertRaises(BusinessRuleError):
            self.service.search_movies(sort_order="DROP TABLE")

    def test_edit_missing_movie(self):
        with self.assertRaises(NotFoundError):
            self.service.edit_movie(999, "Нет", 90)

    def test_delete_movie_success(self):
        movie = self.service.add_movie("Удаляемый", 90)
        self.assertTrue(self.service.delete_movie(movie["id"], confirmed=True)["deleted"])
        self.assertIsNone(self.movie_dao.getById(movie["id"]))

    def test_delete_cancelled_keeps_movie(self):
        movie = self.service.add_movie("Оставить", 90)
        result = self.service.delete_movie(movie["id"], confirmed=False)
        self.assertFalse(result["deleted"])
        self.assertIsNotNone(self.movie_dao.getById(movie["id"]))

    def test_search_by_genre(self):
        self.service.add_movie("Фантастический фильм", 100, 8, 1, [1])
        self.service.add_movie("Другой фильм", 90, 7, 1)
        result = self.service.search_movies(genre_id=1)
        self.assertEqual([m["title"] for m in result], ["Фантастический фильм"])

    def test_delete_missing_movie(self):
        with self.assertRaises(NotFoundError):
            self.service.delete_movie(999, confirmed=True)

    def test_search_and_filter(self):
        self.service.add_movie("Интерстеллар", 169, 8.6, 1)
        self.service.add_movie("Дюна", 155, 8.0, 2)
        result = self.service.search_movies(query="дюн", min_rating=7, status_id=2)
        self.assertEqual([movie["title"] for movie in result], ["Дюна"])

    def test_search_rejects_wrong_sort(self):
        with self.assertRaises(BusinessRuleError):
            self.service.search_movies(sort_by="title; DROP TABLE movies")

    def test_change_status(self):
        movie = self.service.add_movie("Фильм", 100, 6.5, 1)
        changed = self.service.change_status(movie["id"], 3)
        self.assertEqual(changed["movie"]["status_id"], 3)

    def test_change_status_rejects_unknown_status(self):
        movie = self.service.add_movie("Фильм", 100)
        with self.assertRaises(BusinessRuleError):
            self.service.change_status(movie["id"], 999)

    def test_statistics(self):
        self.service.add_movie("Фильм", 100, 8.0, 1, [1], [(1, "режиссёр")])
        stats = self.service.get_statistics()
        self.assertEqual(stats["summary"]["total_count"], 1)
        self.assertEqual(len(stats["top_genres"]), 1)

    def test_statistics_rejects_bad_limit(self):
        with self.assertRaises(BusinessRuleError):
            self.service.get_statistics(top_limit=0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
