"""
Introspection dla custom PostgreSQL backend.
"""
from django.db.backends.postgresql import introspection as postgresql_introspection

__all__ = ['DatabaseIntrospection']

# Dziedziczymy wszystkie introspection z PostgreSQL
DatabaseIntrospection = postgresql_introspection.DatabaseIntrospection

