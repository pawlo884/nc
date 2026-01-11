"""
Ulepszony system logowania dla operacji między bazami danych
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from contextlib import contextmanager
from django.db.models import Model


class TransactionLogger:
    """
    Logger do śledzenia operacji między bazami danych
    """

    def __init__(self, operation_name: str, logger_name: str = None):
        self.operation_name = operation_name
        self.logger = logging.getLogger(
            logger_name or f"transaction.{operation_name}")
        self.start_time = None
        self.operations_log = []
        self.databases_involved = set()

    def log_operation(self,
                      operation_type: str,
                      database: str,
                      table: str,
                      action: str,
                      data: Dict[str, Any] = None,
                      success: bool = True,
                      error: str = None):
        """
        Loguj pojedynczą operację na bazie danych

        Args:
            operation_type: Typ operacji (SELECT, INSERT, UPDATE, DELETE)
            database: Nazwa bazy danych
            table: Nazwa tabeli
            action: Opis akcji
            data: Dane operacji
            success: Czy operacja się powiodła
            error: Błąd jeśli wystąpił
        """
        operation_log = {
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'database': database,
            'table': table,
            'action': action,
            'success': success,
            'error': error,
            'data': data
        }

        self.operations_log.append(operation_log)
        self.databases_involved.add(database)

        # Log poziom w zależności od powodzenia
        if success:
            self.logger.info(
                "[%s] %s %s.%s: %s",
                database, operation_type, table, action,
                json.dumps(data, default=str) if data else "OK"
            )
        else:
            self.logger.error(
                "[%s] %s %s.%s FAILED: %s - %s",
                database, operation_type, table, action, error,
                json.dumps(data, default=str) if data else "ERROR"
            )

    def log_cross_database_operation(self,
                                     from_db: str,
                                     to_db: str,
                                     operation: str,
                                     data: Dict[str, Any] = None,
                                     success: bool = True,
                                     error: str = None):
        """
        Loguj operację między bazami danych
        """
        self.log_operation(
            operation_type="CROSS_DB",
            database=f"{from_db}->{to_db}",
            table="cross_database",
            action=operation,
            data=data,
            success=success,
            error=error
        )

    def start_transaction(self):
        """Rozpocznij transakcję"""
        self.start_time = datetime.now()
        self.logger.info(
            "[TRANSACTION] Rozpoczęto operację: %s",
            self.operation_name
        )

    def end_transaction(self, success: bool = True, error: str = None):
        """Zakończ transakcję"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()

            if success:
                self.logger.info(
                    "[TRANSACTION] Zakończono pomyślnie: %s (%.2fs, %d operacji, bazy: %s)",
                    self.operation_name, duration, len(self.operations_log),
                    ', '.join(sorted(self.databases_involved))
                )
            else:
                self.logger.error(
                    "[TRANSACTION] BŁĄD: %s (%.2fs, %d operacji, bazy: %s) - %s",
                    self.operation_name, duration, len(self.operations_log),
                    ', '.join(sorted(self.databases_involved)), error
                )

        # Zwróć podsumowanie
        return {
            'operation': self.operation_name,
            'success': success,
            'duration': duration if self.start_time else 0,
            'operations_count': len(self.operations_log),
            'databases_involved': list(self.databases_involved),
            'error': error,
            'operations': self.operations_log
        }


@contextmanager
def logged_transaction(operation_name: str, logger_name: str = None):
    """
    Context manager do logowania transakcji między bazami

    Usage:
        with logged_transaction("product_mapping") as logger:
            # operacje między bazami
            logger.log_cross_database_operation("matterhorn1", "MPD", "create_product", data)
    """
    logger = TransactionLogger(operation_name, logger_name)
    logger.start_transaction()

    try:
        yield logger
        logger.end_transaction(success=True)
    except Exception as e:
        logger.end_transaction(success=False, error=str(e))
        raise


class DatabaseOperationTracker:
    """
    Tracker do śledzenia operacji na bazach danych
    """

    @staticmethod
    def track_cursor_operation(database: str,
                               operation: str,
                               query: str = None,
                               params: List = None,
                               result_count: int = None,
                               success: bool = True,
                               error: str = None):
        """
        Trackuj operację na cursorze
        """
        logger = logging.getLogger(f"db_operations.{database}")

        log_data = {
            'query': query[:100] + "..." if query and len(query) > 100 else query,
            'params_count': len(params) if params else 0,
            'result_count': result_count
        }

        if success:
            logger.info(
                "[%s] %s - %s",
                database, operation, json.dumps(log_data)
            )
        else:
            logger.error(
                "[%s] %s FAILED - %s - ERROR: %s",
                database, operation, json.dumps(log_data), error
            )

    @staticmethod
    def track_model_operation(model: Model,
                              operation: str,
                              data: Dict[str, Any] = None,
                              success: bool = True,
                              error: str = None):
        """
        Trackuj operację na modelu Django
        """
        database = model._state.db or 'default'
        logger = logging.getLogger(f"model_operations.{database}")

        log_data = {
            'model': f"{model._meta.app_label}.{model._meta.model_name}",
            'pk': getattr(model, 'pk', None),
            'data': data
        }

        if success:
            logger.info(
                "[%s] MODEL %s - %s",
                database, operation, json.dumps(log_data, default=str)
            )
        else:
            logger.error(
                "[%s] MODEL %s FAILED - %s - ERROR: %s",
                database, operation, json.dumps(log_data, default=str), error
            )


def setup_transaction_logging():
    """
    Skonfiguruj logowanie transakcji
    """
    # Logger dla transakcji między bazami
    transaction_logger = logging.getLogger('transaction')
    transaction_logger.setLevel(logging.INFO)

    # Logger dla operacji na bazach danych
    db_operations_logger = logging.getLogger('db_operations')
    db_operations_logger.setLevel(logging.INFO)

    # Logger dla operacji na modelach
    model_operations_logger = logging.getLogger('model_operations')
    model_operations_logger.setLevel(logging.INFO)

    # Sprawdź czy handler już istnieje
    if not transaction_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        transaction_logger.addHandler(handler)
        db_operations_logger.addHandler(handler)
        model_operations_logger.addHandler(handler)


# Automatyczne ustawienie logowania przy imporcie
setup_transaction_logging()
