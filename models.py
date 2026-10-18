from dataclasses import dataclass
from typing import Optional

@dataclass
class Movie:
    title: str
    duration: int
    rating: Optional[float]
    status_id: int
    id: Optional[int] = None

@dataclass
class CollectionSummaryDTO:
    total_movies_count: int
    average_collection_rating: Optional[float]

@dataclass
class PersonStatsDTO:
    person_name: str
    movies_count: int
    average_movies_rating: Optional[float]

@dataclass
class StatusReportDTO:
    status_name: str
    movies_count: int

@dataclass
class GenreReportDTO:
    genre_name: str
    total_movies_in_genre: int
