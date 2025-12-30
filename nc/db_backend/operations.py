"""
Operations dla custom PostgreSQL backend.
"""
from django.db.backends.postgresql import operations as postgresql_operations

__all__ = ['DatabaseOperations']

# Dziedziczymy wszystkie operations z PostgreSQL
DatabaseOperations = postgresql_operations.DatabaseOperations

