import unittest
from movie_dao import MovieDAO
from stats_dao import StatsDAO
from models import Movie

class DAOTests(unittest.TestCase):
    def setUp(self):
        self.movies = MovieDAO()
        self.stats = StatsDAO()

    def test_get_all_returns_list(self):
        self.assertIsInstance(self.movies.getAll(), list)

    def test_insert_get_update_delete(self):
        movie = Movie("DAO тест", 95, 6.5, 1)
        self.assertTrue(self.movies.insert(movie))
        self.assertIsNotNone(movie.id)
        loaded = self.movies.getById(movie.id)
        self.assertEqual(loaded.title, "DAO тест")

        loaded.title = "DAO тест обновлён"
        self.assertTrue(self.movies.update(loaded))
        self.assertEqual(self.movies.getById(movie.id).title, "DAO тест обновлён")
        self.assertTrue(self.movies.delete(movie.id))
        self.assertIsNone(self.movies.getById(movie.id))

    def test_summary_stats(self):
        result = self.stats.getCollectionSummaryStats()
        self.assertGreaterEqual(result.total_movies_count, 0)

    def test_reports_return_lists(self):
        self.assertIsInstance(self.stats.getTopMoviePersonsByRole("Режиссер", 5), list)
        self.assertIsInstance(self.stats.getMoviesDistributionByStatus(), list)
        self.assertIsInstance(self.stats.getTopGenresReport(), list)

if __name__ == "__main__":
    unittest.main(verbosity=2)
