from backend.repositories.base import StoredQuizRecord, StudyRepository
from backend.repositories.memory_repo import InMemoryRepository
from backend.repositories.postgres_repo import PostgresRepository

__all__ = [
    "StoredQuizRecord",
    "StudyRepository",
    "InMemoryRepository",
    "PostgresRepository",
]
