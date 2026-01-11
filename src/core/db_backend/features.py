"""
Features dla custom PostgreSQL backend.
"""
from django.db.backends.postgresql import features as postgresql_features

__all__ = ['DatabaseFeatures']

# Dziedziczymy wszystkie features z PostgreSQL
DatabaseFeatures = postgresql_features.DatabaseFeatures

