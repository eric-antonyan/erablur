from .database import db, Database

try:
    from .mongo_database import MongoDatabase
except Exception:  # PyMongo is optional until requirements are installed.
    MongoDatabase = None  # type: ignore[assignment]

__all__ = ["db", "Database", "MongoDatabase"]
