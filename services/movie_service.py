"""@package movie_service
@brief Бизнес-логика менеджера личной коллекции фильмов.

SQL здесь отсутствует: все обращения к БД выполняются через DAO.

@author Ваше Имя
@date 12.11.2026
@version 1.0
"""
import logging
import sqlite3

logger = logging.getLogger(__name__)


class BusinessRuleError(ValueError):
    """@brief Исключение, возникающее при нарушении бизнес-правил.

    Используется для сигнализации об ошибках валидации входных данных
    или нарушении бизнес-логики сервиса.
    """


class NotFoundError(LookupError):
    """@brief Исключение, возникающее, если запрошенная запись не найдена.

    Наследуется от LookupError и используется при попытке обратиться
    к несуществующему фильму, статусу, жанру или персоне.
    """


class MovieService:
    """@brief Сервис бизнес-логики для управления коллекцией фильмов.

    Отвечает за валидацию входных данных, проверку бизнес-правил
    и координацию операций между MovieDAO и StatsDAO.
    Не содержит SQL — все обращения к БД делегируются DAO-слою.
    """

    ## @brief Допустимые роли персон, связанных с фильмом.
    VALID_ROLES = {"режиссёр", "режиссер", "актёр", "актер", "сценарист", "композитор"}

    def __init__(self, movie_dao, stats_dao, connection):
        """@brief Конструктор сервиса.

        @param movie_dao Объект DAO для работы с таблицей фильмов.
        @param stats_dao Объект DAO для работы со справочниками и статистикой.
        @param connection Объект соединения с SQLite (используется для транзакций).
        """
        self.movie_dao = movie_dao
        self.stats_dao = stats_dao
        self.connection = connection

    @staticmethod
    def _positive_int(value, field_name):
        """@brief Преобразует значение в положительное целое число.

        Проверяет тип, отсутствие булевых значений, корректность строкового
        представления и положительность результата.

        @param value Исходное значение (int, str или совместимый тип).
        @param field_name Название поля для формирования текста ошибки.
        @return Преобразованное положительное целое число.
        @exception BusinessRuleError Если значение не является положительным целым.
        """
        if isinstance(value, bool):
            raise BusinessRuleError(
                f"Поле «{field_name}» должно быть положительным целым числом."
            )
        try:
            converted = int(value)
        except (TypeError, ValueError):
            raise BusinessRuleError(
                f"Поле «{field_name}» должно быть положительным целым числом."
            )
        if str(value).strip() != str(converted) or converted <= 0:
            raise BusinessRuleError(
                f"Поле «{field_name}» должно быть положительным целым числом."
            )
        return converted

    @staticmethod
    def _validate_movie_data(title, duration, rating, status_id):
        """@brief Валидирует основные поля фильма.

        @param title Название фильма.
        @param duration Продолжительность в минутах.
        @param rating Оценка от 0 до 10 (может быть None).
        @param status_id Идентификатор статуса просмотра.
        @return Словарь с нормализованными полями:
                - title (str)
                - duration (int)
                - rating (float | None)
                - status_id (int)
        @exception BusinessRuleError При нарушении любого из правил валидации.
        """
        title = str(title or "").strip()
        if not title:
            raise BusinessRuleError("Название фильма не может быть пустым.")
        duration = MovieService._positive_int(duration, "Продолжительность")
        if rating is not None:
            if isinstance(rating, bool):
                raise BusinessRuleError("Оценка должна быть числом от 0 до 10.")
            try:
                rating = float(rating)
            except (TypeError, ValueError):
                raise BusinessRuleError("Оценка должна быть числом от 0 до 10.")
            if not 0 <= rating <= 10:
                raise BusinessRuleError("Оценка должна быть числом от 0 до 10.")
        status_id = MovieService._positive_int(status_id, "ID статуса")
        return {
            "title": title,
            "duration": duration,
            "rating": rating,
            "status_id": status_id,
        }

    def _ensure_status_exists(self, status_id):
        """@brief Проверяет, что статус с указанным ID существует в справочнике.

        @param status_id Идентификатор статуса.
        @exception BusinessRuleError Если статус не найден.
        """
        if not self.stats_dao.status_exists(status_id):
            raise BusinessRuleError(f"Статус с ID {status_id} не существует.")

    def _validate_links(self, genre_ids=None, persons=None):
        """@brief Валидирует связи фильма с жанрами и персонами.

        Проверяет типы, существование жанров и персон в справочниках,
        а также допустимость ролей персон.

        @param genre_ids Список идентификаторов жанров (или None).
        @param persons Список кортежей (person_id, role) (или None).
        @return Кортеж (уникальные genre_ids, нормализованные persons).
        @exception BusinessRuleError При нарушении правил связывания.
        """
        genre_ids = list(genre_ids or [])
        persons = list(persons or [])
        for gid in genre_ids:
            self._positive_int(gid, "ID жанра")
        for person in persons:
            if not isinstance(person, (tuple, list)) or len(person) != 2:
                raise BusinessRuleError("Персона должна задаваться парой (ID, роль).")
            self._positive_int(person[0], "ID персоны")
            role = str(person[1] or "").strip().lower()
            if not role:
                raise BusinessRuleError("Роль персоны не может быть пустой.")
            if role not in self.VALID_ROLES:
                raise BusinessRuleError(
                    "Неизвестная роль. Допустимые роли: "
                    + ", ".join(sorted(self.VALID_ROLES))
                )
        if not self.stats_dao.exists_ids("genres", genre_ids):
            raise BusinessRuleError("Один или несколько указанных жанров не существуют.")
        if not self.stats_dao.exists_ids("persons", [p[0] for p in persons]):
            raise BusinessRuleError("Одна или несколько указанных персон не существуют.")
        return list(dict.fromkeys(genre_ids)), [
            (int(pid), str(role).strip().lower()) for pid, role in persons
        ]

    def add_movie(self, title, duration, rating=None, status_id=1,
                  genre_ids=None, persons=None):
        """@brief Добавляет новый фильм в коллекцию.

        Выполняет валидацию данных, проверку существования статуса,
        жанров и персон, после чего сохраняет фильм и его связи
        в рамках одной транзакции.

        @param title Название фильма.
        @param duration Продолжительность в минутах.
        @param rating Оценка от 0 до 10 (по умолчанию None).
        @param status_id ID статуса просмотра (по умолчанию 1).
        @param genre_ids Список ID жанров (или None).
        @param persons Список кортежей (person_id, role) (или None).
        @return Словарь с данными созданного фильма.
        @exception BusinessRuleError При ошибке валидации или БД.

        @code
        movie = service.add_movie(
            title="Интерстеллар",
            duration=169,
            rating=8.6,
            status_id=2,
            genre_ids=[1, 3],
            persons=[(10, "режиссёр")]
        )
        @endcode
        """
        data = self._validate_movie_data(title, duration, rating, status_id)
        self._ensure_status_exists(data["status_id"])
        genre_ids, persons = self._validate_links(genre_ids, persons)
        try:
            with self.connection:
                movie_id = self.movie_dao.insert(data)
                self.stats_dao.replace_movie_links(movie_id, genre_ids, persons)
            return self.movie_dao.getById(movie_id)
        except sqlite3.Error as exc:
            logger.exception("Не удалось добавить фильм")
            raise BusinessRuleError(
                "Не удалось добавить фильм: ошибка базы данных."
            ) from exc

    def edit_movie(self, movie_id, title=None, duration=None, rating=...,
                   status_id=None, genre_ids=None, persons=None):
        """@brief Изменяет существующий фильм.

        Изменяет только переданные поля; остальные сохраняет без изменений.
        Если переданы genre_ids или persons — заменяет связи полностью.

        @param movie_id Идентификатор фильма.
        @param title Новое название (None — не изменять).
        @param duration Новая продолжительность (None — не изменять).
        @param rating Новая оценка (`...` — не изменять).
        @param status_id Новый ID статуса (None — не изменять).
        @param genre_ids Новый список жанров (None — не изменять).
        @param persons Новый список персон (None — не изменять).
        @return Словарь с обновлёнными данными фильма.
        @exception NotFoundError Если фильм не найден.
        @exception BusinessRuleError При ошибке валидации или БД.
        """
        movie_id = self._positive_int(movie_id, "ID фильма")
        try:
            current = self.movie_dao.getById(movie_id)
            if not current:
                raise NotFoundError(f"Фильм с ID {movie_id} не найден.")
            data = {
                "title": current["title"] if title is None else title,
                "duration": current["duration"] if duration is None else duration,
                "rating": current["rating"] if rating is ... else rating,
                "status_id": current["status_id"] if status_id is None else status_id,
            }
            data = self._validate_movie_data(**data)
            self._ensure_status_exists(data["status_id"])
            links_provided = genre_ids is not None or persons is not None
            if links_provided:
                old_links = self.stats_dao.get_movie_links(movie_id)
                genre_ids = old_links["genre_ids"] if genre_ids is None else genre_ids
                persons = old_links["persons"] if persons is None else persons
                genre_ids, persons = self._validate_links(genre_ids, persons)
            data["id"] = movie_id
            with self.connection:
                if not self.movie_dao.update(data):
                    raise NotFoundError(f"Фильм с ID {movie_id} не найден.")
                if links_provided:
                    self.stats_dao.replace_movie_links(movie_id, genre_ids, persons)
            return self.movie_dao.getById(movie_id)
        except (BusinessRuleError, NotFoundError):
            raise
        except sqlite3.Error as exc:
            logger.exception("Не удалось изменить фильм")
            raise BusinessRuleError(
                "Не удалось обновить фильм. Данные не сохранены."
            ) from exc

    def delete_movie(self, movie_id, confirmed=False):
        """@brief Удаляет фильм из коллекции.

        Требует явного подтверждения (confirmed=True) для предотвращения
        случайного удаления.

        @param movie_id Идентификатор фильма.
        @param confirmed Флаг подтверждения удаления (по умолчанию False).
        @return Словарь вида {"deleted": bool, "message": str}.
        @exception NotFoundError Если фильм не найден при подтверждённом удалении.
        @exception BusinessRuleError При ошибке БД.
        """
        movie_id = self._positive_int(movie_id, "ID фильма")
        if not confirmed:
            return {"deleted": False, "message": "Удаление отменено."}
        if not self.movie_dao.getById(movie_id):
            raise NotFoundError(f"Фильм с ID {movie_id} не найден.")
        try:
            with self.connection:
                deleted = self.movie_dao.delete(movie_id)
                if not deleted:
                    raise NotFoundError(f"Фильм с ID {movie_id} не найден.")
            return {"deleted": True, "message": "Фильм удалён."}
        except sqlite3.Error as exc:
            logger.exception("Не удалось удалить фильм")
            raise BusinessRuleError(
                "Не удалось удалить фильм: ошибка базы данных."
            ) from exc

    def search_movies(self, query="", genre_id=None, status_id=None,
                      min_rating=None, max_rating=None, sort_by="title",
                      sort_order="ASC", descending=None):
        """@brief Поиск и фильтрация фильмов по различным критериям.

        Поддерживает текстовый поиск, фильтрацию по жанру, статусу,
        диапазону оценок и сортировку.

        @param query Текстовый запрос для поиска по названию.
        @param genre_id ID жанра для фильтрации (или None).
        @param status_id ID статуса для фильтрации (или None).
        @param min_rating Минимальная оценка (0–10, или None).
        @param max_rating Максимальная оценка (0–10, или None).
        @param sort_by Поле сортировки: "title", "rating" или "duration".
        @param sort_order Направление: "ASC" или "DESC".
        @param descending Устаревший параметр; при передаче переопределяет sort_order.
        @return Список словарей с данными найденных фильмов.
        @exception BusinessRuleError При некорректных параметрах поиска.

        @see MovieDAO.search_movies()
        """
        query = str(query or "").strip()
        allowed_sort = {"title", "rating", "duration"}
        if sort_by not in allowed_sort:
            raise BusinessRuleError(
                "Сортировка разрешена только по названию, оценке или продолжительности."
            )
        if descending is not None:
            sort_order = "DESC" if descending else "ASC"
        if not isinstance(sort_order, str) or sort_order.upper() not in {"ASC", "DESC"}:
            raise BusinessRuleError("Направление сортировки должно быть ASC или DESC.")
        sort_order = sort_order.upper()
        try:
            if min_rating is not None:
                min_rating = float(min_rating)
                if not 0 <= min_rating <= 10:
                    raise BusinessRuleError("Минимальная оценка должна быть от 0 до 10.")
            if max_rating is not None:
                max_rating = float(max_rating)
                if not 0 <= max_rating <= 10:
                    raise BusinessRuleError("Максимальная оценка должна быть от 0 до 10.")
        except (TypeError, ValueError) as exc:
            if isinstance(exc, BusinessRuleError):
                raise
            raise BusinessRuleError("Оценки должны быть числами от 0 до 10.") from exc
        if min_rating is not None and max_rating is not None and min_rating > max_rating:
            raise BusinessRuleError("Минимальная оценка больше максимальной.")
        if genre_id is not None:
            genre_id = self._positive_int(genre_id, "ID жанра")
            if not self.stats_dao.exists_ids("genres", [genre_id]):
                raise BusinessRuleError(f"Жанр с ID {genre_id} не существует.")
        if status_id is not None:
            status_id = self._positive_int(status_id, "ID статуса")
            self._ensure_status_exists(status_id)
        try:
            return self.movie_dao.search_movies(
                query=query,
                genre_id=genre_id,
                status_id=status_id,
                min_rating=min_rating,
                max_rating=max_rating,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        except sqlite3.Error as exc:
            logger.exception("Не удалось выполнить поиск фильмов")
            raise BusinessRuleError(
                "Не удалось выполнить поиск: ошибка базы данных."
            ) from exc

    def change_status(self, movie_id, status_id):
        """@brief Изменяет статус просмотра фильма.

        @param movie_id Идентификатор фильма.
        @param status_id Новый ID статуса.
        @return Словарь {"movie": dict, "message": str}.
        @exception NotFoundError Если фильм не найден.
        @exception BusinessRuleError Если статус не существует или ошибка БД.
        """
        movie_id = self._positive_int(movie_id, "ID фильма")
        status_id = self._positive_int(status_id, "ID статуса")
        movie = self.movie_dao.getById(movie_id)
        if not movie:
            raise NotFoundError(f"Фильм с ID {movie_id} не найден.")
        self._ensure_status_exists(status_id)
        if movie["status_id"] == status_id:
            return {"movie": movie, "message": "Фильм уже имеет этот статус."}
        movie["status_id"] = status_id
        try:
            with self.connection:
                if not self.movie_dao.update(movie):
                    raise NotFoundError(f"Фильм с ID {movie_id} не найден.")
            return {
                "movie": self.movie_dao.getById(movie_id),
                "message": "Статус фильма изменён.",
            }
        except sqlite3.Error as exc:
            logger.exception("Не удалось изменить статус фильма")
            raise BusinessRuleError(
                "Не удалось изменить статус: ошибка базы данных."
            ) from exc

    def get_statistics(self, top_limit=5, person_role="режиссёр"):
        """@brief Формирует сводную статистику по коллекции фильмов.

        Включает общую сводку, топ персон по роли, распределение по статусам
        и топ жанров.

        @param top_limit Количество элементов в рейтингах (1–20, по умолчанию 5).
        @param person_role Роль персоны для топ-рейтинга (по умолчанию "режиссёр").
        @return Словарь с ключами:
                - summary
                - top_persons
                - status_distribution
                - top_genres
        @exception BusinessRuleError При некорректных параметрах или ошибке БД.

        @see StatsDAO.getCollectionSummaryStats()
        @see StatsDAO.getTopMoviePersonsByRole()
        """
        top_limit = self._positive_int(top_limit, "Количество элементов статистики")
        if top_limit > 20:
            raise BusinessRuleError("Размер рейтинга должен быть от 1 до 20.")
        role = str(person_role or "").strip().lower()
        if role not in self.VALID_ROLES:
            raise BusinessRuleError("Указана неизвестная роль персоны.")
        try:
            return {
                "summary": self.stats_dao.getCollectionSummaryStats(),
                "top_persons": self.stats_dao.getTopMoviePersonsByRole(role, top_limit),
                "status_distribution": self.stats_dao.getMoviesDistributionByStatus(),
                "top_genres": self.stats_dao.getTopGenresReport(top_limit),
            }
        except sqlite3.Error as exc:
            logger.exception("Не удалось получить статистику")
            raise BusinessRuleError(
                "Не удалось получить статистику: ошибка базы данных."
            ) from exc
