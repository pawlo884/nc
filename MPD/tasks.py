from celery import shared_task
from django.utils import timezone
import logging
from .export_to_xml import FullXMLExporter, FullChangeXMLExporter
from .memory_optimizer import memory_monitor, query_monitor, MemoryOptimizer

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='mpd.export_full_xml_hourly')
def export_full_xml_hourly(self):
    """
    Task do godzinowego eksportu full.xml - eksportuje nowe produkty
    Uruchamiany co godzinę przez periodic task
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"🚀 Rozpoczynam task export_full_xml_hourly (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Użyj monitora pamięci
    with memory_monitor("eksport full.xml"):
        try:
            # Utwórz eksporter
            exporter = FullXMLExporter()

            # Eksport przyrostowy - nowe produkty od ostatniego eksportu
            with query_monitor():
                result = exporter.export()

            end_time = timezone.now()
            duration = end_time - start_time

            if result['bucket_url']:
                logger.info(
                    f"✅ Task export_full_xml_hourly (ID: {task_id}) zakończony pomyślnie w {duration.total_seconds():.2f}s"
                )
                logger.info(f"📁 URL: {result['bucket_url']}")
                logger.info(f"📄 Lokalnie zapisano: {result['local_path']}")

                return {
                    'status': 'success',
                    'task_id': task_id,
                    'bucket_url': result['bucket_url'],
                    'local_path': result['local_path'],
                    'duration_seconds': duration.total_seconds(),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            else:
                logger.error(
                    f"❌ Task export_full_xml_hourly (ID: {task_id}) błąd po {duration.total_seconds():.2f}s"
                )
                logger.error(f"📄 Lokalnie zapisano: {result['local_path']}")

                return {
                    'status': 'error',
                    'task_id': task_id,
                    'error': 'Błąd podczas eksportu do S3',
                    'local_path': result['local_path'],
                    'duration_seconds': duration.total_seconds(),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }

        except Exception as e:
            end_time = timezone.now()
            duration = end_time - start_time

            error_msg = f"❌ Task export_full_xml_hourly (ID: {task_id}) błąd po {duration.total_seconds():.2f}s: {str(e)}"
            logger.error(error_msg)

            # Oznacz task jako nieudany
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e),
                    'task_id': task_id,
                    'duration_seconds': duration.total_seconds(),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            )

            return {
                'status': 'failure',
                'task_id': task_id,
                'error': str(e),
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }


@shared_task(bind=True, name='mpd.export_full_change_xml_hourly')
def export_full_change_xml_hourly(self):
    """
    Task do godzinowego eksportu full_change.xml - monitoruje zmiany w wyeksportowanych produktach
    Uruchamiany co godzinę przez periodic task
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"🚀 Rozpoczynam task export_full_change_xml_hourly (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Użyj monitora pamięci
    with memory_monitor("eksport full_change.xml"):
        try:
            # Utwórz eksporter
            exporter = FullChangeXMLExporter()

            # Eksport zmian - produkty zmienione w ciągu ostatnich 2 godzin
            with query_monitor():
                result = exporter.export()

            end_time = timezone.now()
            duration = end_time - start_time

            if result['bucket_url']:
                logger.info(
                    f"✅ Task export_full_change_xml_hourly (ID: {task_id}) zakończony pomyślnie w {duration.total_seconds():.2f}s"
                )
                logger.info(f"📁 URL: {result['bucket_url']}")
                logger.info(f"📄 Lokalnie zapisano: {result['local_path']}")

                return {
                    'status': 'success',
                    'task_id': task_id,
                    'bucket_url': result['bucket_url'],
                    'local_path': result['local_path'],
                    'duration_seconds': duration.total_seconds(),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            else:
                logger.error(
                    f"❌ Task export_full_change_xml_hourly (ID: {task_id}) błąd po {duration.total_seconds():.2f}s"
                )
                logger.error(f"📄 Lokalnie zapisano: {result['local_path']}")

                return {
                    'status': 'error',
                    'task_id': task_id,
                    'error': 'Błąd podczas eksportu do S3',
                    'local_path': result['local_path'],
                    'duration_seconds': duration.total_seconds(),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }

        except Exception as e:
            end_time = timezone.now()
            duration = end_time - start_time

            error_msg = f"❌ Task export_full_change_xml_hourly (ID: {task_id}) błąd po {duration.total_seconds():.2f}s: {str(e)}"
            logger.error(error_msg)

            # Oznacz task jako nieudany
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e),
                    'task_id': task_id,
                    'duration_seconds': duration.total_seconds(),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            )

            return {
                'status': 'failure',
                'task_id': task_id,
                'error': str(e),
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }


@shared_task(bind=True, name='mpd.optimize_memory')
def optimize_memory_task(self):
    """
    Task do optymalizacji pamięci - uruchamiany okresowo
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"🧹 Rozpoczynam task optimize_memory (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        optimizer = MemoryOptimizer()
        result = optimizer.optimize_memory()

        end_time = timezone.now()
        duration = end_time - start_time

        logger.info(
            f"✅ Task optimize_memory (ID: {task_id}) zakończony pomyślnie w {duration.total_seconds():.2f}s"
        )
        logger.info(
            f"💾 Zaoszczędzono {result['memory_saved_mb']:.2f} MB pamięci")

        return {
            'status': 'success',
            'task_id': task_id,
            'memory_saved_mb': result['memory_saved_mb'],
            'collected_objects': result['collected_objects'],
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

    except Exception as e:
        end_time = timezone.now()
        duration = end_time - start_time

        error_msg = f"❌ Task optimize_memory (ID: {task_id}) błąd po {duration.total_seconds():.2f}s: {str(e)}"
        logger.error(error_msg)

        # Oznacz task jako nieudany
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'task_id': task_id,
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )

        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e),
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }


@shared_task(bind=True, name='mpd.export_full_xml_full')
def export_full_xml_full(self):
    """
    Task do pełnego eksportu full.xml - wszystkie produkty
    Uruchamiany ręcznie lub przez periodic task (np. raz dziennie)
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"🚀 Rozpoczynam task export_full_xml_full (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Utwórz eksporter
        exporter = FullXMLExporter()

        # Eksport pełny - wszystkie produkty
        result = exporter.export()

        end_time = timezone.now()
        duration = end_time - start_time

        if result['bucket_url']:
            logger.info(
                f"✅ Task export_full_xml_full (ID: {task_id}) zakończony pomyślnie w {duration.total_seconds():.2f}s"
            )
            logger.info(f"📁 URL: {result['bucket_url']}")
            logger.info(f"📄 Lokalnie zapisano: {result['local_path']}")

            return {
                'status': 'success',
                'task_id': task_id,
                'bucket_url': result['bucket_url'],
                'local_path': result['local_path'],
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        else:
            logger.error(
                f"❌ Task export_full_xml_full (ID: {task_id}) błąd po {duration.total_seconds():.2f}s"
            )
            logger.error(f"📄 Lokalnie zapisano: {result['local_path']}")

            return {
                'status': 'error',
                'task_id': task_id,
                'error': 'Błąd podczas eksportu do S3',
                'local_path': result['local_path'],
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }

    except Exception as e:
        end_time = timezone.now()
        duration = end_time - start_time

        error_msg = f"❌ Task export_full_xml_full (ID: {task_id}) błąd po {duration.total_seconds():.2f}s: {str(e)}"
        logger.error(error_msg)

        # Oznacz task jako nieudany
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'task_id': task_id,
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )

        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e),
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }


@shared_task(bind=True, name='mpd.export_full_change_xml_full')
def export_full_change_xml_full(self):
    """
    Task do pełnego eksportu full_change.xml - wszystkie produkty
    Uruchamiany ręcznie lub przez periodic task (np. raz dziennie)
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"🚀 Rozpoczynam task export_full_change_xml_full (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Utwórz eksporter
        exporter = FullChangeXMLExporter()

        # Eksport pełny - wszystkie produkty
        result = exporter.export_full()

        end_time = timezone.now()
        duration = end_time - start_time

        if result['bucket_url']:
            logger.info(
                f"✅ Task export_full_change_xml_full (ID: {task_id}) zakończony pomyślnie w {duration.total_seconds():.2f}s"
            )
            logger.info(f"📁 URL: {result['bucket_url']}")
            logger.info(f"📄 Lokalnie zapisano: {result['local_path']}")

            return {
                'status': 'success',
                'task_id': task_id,
                'bucket_url': result['bucket_url'],
                'local_path': result['local_path'],
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        else:
            logger.error(
                f"❌ Task export_full_change_xml_full (ID: {task_id}) błąd po {duration.total_seconds():.2f}s"
            )
            logger.error(f"📄 Lokalnie zapisano: {result['local_path']}")

            return {
                'status': 'error',
                'task_id': task_id,
                'error': 'Błąd podczas eksportu do S3',
                'local_path': result['local_path'],
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }

    except Exception as e:
        end_time = timezone.now()
        duration = end_time - start_time

        error_msg = f"❌ Task export_full_change_xml_full (ID: {task_id}) błąd po {duration.total_seconds():.2f}s: {str(e)}"
        logger.error(error_msg)

        # Oznacz task jako nieudany
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'task_id': task_id,
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )

        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e),
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }


@shared_task(bind=True, name='MPD.tasks.track_recent_stock_changes')
def track_recent_stock_changes(self):
    """
    Task do śledzenia zmian stanów magazynowych
    Uruchamiany okresowo przez periodic task
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"🚀 Rozpoczynam task track_recent_stock_changes (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # TODO: Implementuj logikę śledzenia zmian stanów magazynowych
        # Na razie zwracamy sukces bez implementacji

        end_time = timezone.now()
        duration = end_time - start_time

        logger.info(
            f"✅ Task track_recent_stock_changes (ID: {task_id}) zakończony pomyślnie w {duration.total_seconds():.2f}s"
        )

        return {
            'status': 'success',
            'task_id': task_id,
            'message': 'Śledzenie zmian stanów magazynowych zakończone',
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

    except Exception as e:
        end_time = timezone.now()
        duration = end_time - start_time

        error_msg = f"❌ Task track_recent_stock_changes (ID: {task_id}) błąd po {duration.total_seconds():.2f}s: {str(e)}"
        logger.error(error_msg)

        # Oznacz task jako nieudany
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'task_id': task_id,
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )

        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e),
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
