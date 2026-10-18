PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    duration INTEGER NOT NULL CHECK (duration > 0),
    rating REAL CHECK (rating IS NULL OR (rating >= 0 AND rating <= 10)),
    status_id INTEGER NOT NULL,
    FOREIGN KEY (status_id) REFERENCES statuses(id)
);

CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, genre_id),
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS movie_persons (
    movie_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (movie_id, person_id, role),
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_movies_status_id ON movies(status_id);
CREATE INDEX IF NOT EXISTS idx_movie_persons_role ON movie_persons(role);
CREATE INDEX IF NOT EXISTS idx_movie_genres_genre_id ON movie_genres(genre_id);

INSERT OR IGNORE INTO statuses(name) VALUES
('В планах'), ('В процессе'), ('Завершено');

INSERT OR IGNORE INTO genres(name) VALUES
('Фантастика'), ('Драма'), ('Комедия'), ('Боевик');

INSERT OR IGNORE INTO persons(full_name) VALUES
('Кристофер Нолан'), ('Стивен Спилберг'), ('Дени Вильнёв');

INSERT INTO movies(title, duration, rating, status_id)
SELECT 'Начало', 148, 8.8, id FROM statuses WHERE name = 'Завершено'
AND NOT EXISTS (SELECT 1 FROM movies WHERE title = 'Начало');

INSERT INTO movies(title, duration, rating, status_id)
SELECT 'Дюна', 155, 8.0, id FROM statuses WHERE name = 'В процессе'
AND NOT EXISTS (SELECT 1 FROM movies WHERE title = 'Дюна');

INSERT INTO movie_genres(movie_id, genre_id)
SELECT m.id, g.id FROM movies m, genres g
WHERE m.title = 'Начало' AND g.name IN ('Фантастика', 'Боевик')
AND NOT EXISTS (
    SELECT 1 FROM movie_genres mg WHERE mg.movie_id=m.id AND mg.genre_id=g.id
);

INSERT INTO movie_genres(movie_id, genre_id)
SELECT m.id, g.id FROM movies m, genres g
WHERE m.title = 'Дюна' AND g.name IN ('Фантастика', 'Драма')
AND NOT EXISTS (
    SELECT 1 FROM movie_genres mg WHERE mg.movie_id=m.id AND mg.genre_id=g.id
);

INSERT INTO movie_persons(movie_id, person_id, role)
SELECT m.id, p.id, 'Режиссер' FROM movies m, persons p
WHERE m.title='Начало' AND p.full_name='Кристофер Нолан'
AND NOT EXISTS (
    SELECT 1 FROM movie_persons mp WHERE mp.movie_id=m.id AND mp.person_id=p.id AND mp.role='Режиссер'
);

INSERT INTO movie_persons(movie_id, person_id, role)
SELECT m.id, p.id, 'Режиссер' FROM movies m, persons p
WHERE m.title='Дюна' AND p.full_name='Дени Вильнёв'
AND NOT EXISTS (
    SELECT 1 FROM movie_persons mp WHERE mp.movie_id=m.id AND mp.person_id=p.id AND mp.role='Режиссер'
);
