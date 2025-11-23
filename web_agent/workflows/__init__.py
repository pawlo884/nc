"""
Workflows - konkretne implementacje workflow dla różnych zadań
"""

from .django_admin import DjangoAdminWorkflow
from .product_mapping import ProductMappingWorkflow

__all__ = ['DjangoAdminWorkflow', 'ProductMappingWorkflow']

