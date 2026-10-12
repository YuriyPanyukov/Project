-- Отключение проверки внешних ключей на время пересоздания таблиц (для надежности)
PRAGMA foreign_keys = OFF;

-- Удаление таблиц, если они уже существуют (для удобства перезапуска скрипта)
DROP TABLE IF EXISTS movie_persons;
DROP TABLE IF EXISTS movie_genres;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS persons;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS statuses;

-- Включение поддержки внешних ключей в SQLite
PRAGMA foreign_keys = ON;

-- 1. Таблица статусов (например: "Анонсирован", "В прокате", "Вышел на DVD")
CREATE TABLE statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL UNIQUE
);

-- 2. Таблица жанров (например: "Драма", "Комедия", "Фантастика")
CREATE TABLE genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL UNIQUE
);

-- 3. Таблица участников (режиссеры, актеры и т.д.)
CREATE TABLE persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name VARCHAR NOT NULL
);

-- 4. Таблица фильмов (главная сущность)
CREATE TABLE movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR NOT NULL,
    duration SMALLINT CHECK (duration > 0), -- Ограничение CHECK: длительность должна быть положительной
    rating DECIMAL CHECK (rating >= 0 AND rating <= 10), -- Ограничение CHECK: рейтинг от 0 до 10
    status_id INTEGER,
    -- Внешний ключ: при удалении статуса, у фильма поле status_id становится NULL
    FOREIGN KEY (status_id) REFERENCES statuses (id) ON DELETE SET NULL
);

-- 5. Промежуточная таблица связи фильмов и жанров (Многие-ко-многим)
CREATE TABLE movie_genres (
    movie_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, genre_id),
    -- При удалении фильма или жанра, соответствующие связи удаляются автоматически (CASCADE)
    FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres (id) ON DELETE CASCADE
);

-- 6. Промежуточная таблица связи фильмов и персон с указанием роли
CREATE TABLE movie_persons (
    movie_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role VARCHAR NOT NULL,
    PRIMARY KEY (movie_id, person_id, role),
    -- При удалении фильма или человека связи удаляются автоматически (CASCADE)
    FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES persons (id) ON DELETE CASCADE
);

-- 3. Создание индексов (для ускорения поиска и JOIN-операций)
CREATE INDEX idx_movies_status_id ON movies(status_id);
CREATE INDEX idx_movie_genres_genre_id ON movie_genres(genre_id);
CREATE INDEX idx_movie_persons_person_id ON movie_persons(person_id);
CREATE INDEX idx_movies_title ON movies(title); -- Для быстрого поиска по названию фильма

-- =====================================================================
-- ШАГ 3. ТЕСТИРОВАНИЕ ВСТАВКИ И ОГРАНИЧЕНИЙ
-- =====================================================================

-- 1. Успешная вставка корректных данных
INSERT INTO statuses (name) VALUES ('Вышел в прокат'), ('Анонсирован');
INSERT INTO genres (name) VALUES ('Фантастика'), ('Драма');
INSERT INTO persons (full_name) VALUES ('Кристофер Нолан'), ('Леонардо Ди Каприо');

INSERT INTO movies (title, duration, rating, status_id) 
VALUES ('Начало', 148, 8.8, 1);

INSERT INTO movie_genres (movie_id, genre_id) VALUES (1, 1), (1, 2);
INSERT INTO movie_persons (movie_id, person_id, role) VALUES (1, 1, 'Режиссер'), (1, 2, 'Актер');


-- 2. ПРОВЕРКА ОГРАНИЧЕНИЙ (Каждый из этих запросов должен вызывать ошибку)

-- Проверка UNIQUE (Вызовет ошибку, так как 'Драма' уже есть)
-- INSERT INTO genres (name) VALUES ('Драма');

-- Проверка CHECK на отрицательное время (Вызовет ошибку)
-- INSERT INTO movies (title, duration, rating) VALUES ('Неправильный фильм', -10, 5.0);

-- Проверка CHECK на рейтинг выше 10 (Вызовет ошибку)
-- INSERT INTO movies (title, duration, rating) VALUES ('Супер фильм', 120, 11.5);


-- 3. ПРОВЕРКА СВЯЗЕЙ И КАШКАДНОГО УДАЛЕНИЯ

-- Проверим работу ON DELETE SET NULL для статуса:
DELETE FROM statuses WHERE id = 1;
-- Проверка: у фильма "Начало" поле status_id теперь должно стать NULL
SELECT id, title, status_id FROM movies WHERE id = 1;

-- Проверим работу ON DELETE CASCADE для связей фильма:
DELETE FROM movies WHERE id = 1;
-- Проверка: записи в movie_genres и movie_persons для movie_id = 1 должны автоматически удалиться
SELECT * FROM movie_genres WHERE movie_id = 1;
SELECT * FROM movie_persons WHERE movie_id = 1;

