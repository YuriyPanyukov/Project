from movie_dao import MovieDAO
from stats_dao import StatsDAO
from models import Movie

def main():
    movies = MovieDAO()
    stats = StatsDAO()

    print("=== Все фильмы ===")
    for movie in movies.getAll():
        print(movie)

    print("\\n=== Поиск фильма с id=1 ===")
    print(movies.getById(1))

    print("\\n=== Добавление тестового фильма ===")
    test_movie = Movie(title="Тестовый фильм", duration=100, rating=7.5, status_id=1)
    if movies.insert(test_movie):
        print(f"Добавлен фильм с id={test_movie.id}")
        test_movie.title = "Тестовый фильм (обновлён)"
        print("Обновление:", movies.update(test_movie))
        print("Удаление:", movies.delete(test_movie.id))

    print("\\n=== Общая статистика ===")
    print(stats.getCollectionSummaryStats())

    print("\\n=== Топ режиссёров ===")
    for row in stats.getTopMoviePersonsByRole("Режиссер", 5):
        print(row)

    print("\\n=== Распределение по статусам ===")
    for row in stats.getMoviesDistributionByStatus():
        print(row)

    print("\\n=== Популярные жанры ===")
    for row in stats.getTopGenresReport():
        print(row)

if __name__ == "__main__":
    main()
