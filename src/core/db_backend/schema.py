"""
Schema dla custom PostgreSQL backend.
"""
from django.db.backends.postgresql import schema as postgresql_schema

__all__ = ['DatabaseSchemaEditor']

# Dziedziczymy wszystkie schema z PostgreSQL
DatabaseSchemaEditor = postgresql_schema.DatabaseSchemaEditor

