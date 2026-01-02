"""
Saga Pattern Implementation for Cross-Database Operations - WEGA

Ten moduł implementuje Saga Pattern do bezpiecznego wykonywania operacji
między różnymi bazami danych (wega, MPD) z automatyczną kompensacją.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass
from django.db import connections
from django.utils import timezone
# Używamy modeli Saga z matterhorn1, ale operujemy na wega
from matterhorn1.models import Saga, SagaStep

logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    """Statusy Saga"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


@dataclass
class SagaStepData:
    """Pojedynczy krok w Saga (dane)"""
    name: str
    execute_func: Callable
    compensate_func: Callable
    data: Dict[str, Any] = None
    status: SagaStatus = SagaStatus.PENDING
    error: Optional[str] = None
    executed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class SagaResult:
    """Wynik wykonania Saga"""
    saga_id: str
    status: SagaStatus
    steps: List[SagaStepData]
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None


class SagaOrchestrator:
    """
    Orchestrator dla Saga Pattern - WEGA
    """

    def __init__(self, saga_id: str = None, saga_type: str = "generic", enable_logging: bool = True):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.saga_type = saga_type
        self.enable_logging = enable_logging
        self.steps: List[SagaStepData] = []
        self.status = SagaStatus.PENDING
        self.created_at = timezone.now()
        self.error = None
        self.saga_log = None

        if self.enable_logging:
            self._create_saga_log()

    def add_step(self, name: str, execute_func: Callable, compensate_func: Callable, data: Dict[str, Any] = None):
        """Dodaj krok do Saga"""
        step = SagaStepData(
            name=name,
            execute_func=execute_func,
            compensate_func=compensate_func,
            data=data or {}
        )
        self.steps.append(step)
        logger.info(f"🔄 Saga {self.saga_id}: Dodano krok '{name}'")

        if self.enable_logging and self.saga_log:
            self._create_step_log(step)

        return self

    def _create_saga_log(self):
        """Utwórz log Saga w bazie danych"""
        try:
            self.saga_log = Saga.objects.using('matterhorn1').create(
                saga_id=self.saga_id,
                saga_type=self.saga_type,
                status=SagaStatus.PENDING.value,
                input_data={},
                total_steps=0
            )
        except Exception as e:
            logger.warning(f"Nie udało się utworzyć logu Saga: {e}")

    def _create_step_log(self, step: SagaStepData):
        """Utwórz log kroku w bazie danych"""
        if not self.saga_log:
            return
        try:
            SagaStep.objects.using('matterhorn1').create(
                saga=self.saga_log,
                step_name=step.name,
                step_order=len(self.steps),
                status=SagaStatus.PENDING.value,
                input_data=step.data or {}
            )
        except Exception as e:
            logger.warning(f"Nie udało się utworzyć logu kroku: {e}")

    def execute(self) -> SagaResult:
        """Wykonaj wszystkie kroki Saga"""
        self.status = SagaStatus.RUNNING
        if self.saga_log:
            self.saga_log.status = SagaStatus.RUNNING.value
            self.saga_log.started_at = timezone.now()
            self.saga_log.total_steps = len(self.steps)
            self.saga_log.save(using='matterhorn1')

        try:
            previous_result = {}
            for i, step in enumerate(self.steps):
                logger.info(f"🔄 Saga {self.saga_id}: Wykonuję krok {i+1}/{len(self.steps)}: {step.name}")

                step.status = SagaStatus.RUNNING
                step.executed_at = timezone.now()

                # Aktualizuj dane kroku z wynikiem poprzedniego
                if step.data is None:
                    step.data = {}
                step.data.update(previous_result)

                try:
                    # Wykonaj krok
                    result = step.execute_func(step.data)
                    step.result = result
                    step.status = SagaStatus.COMPLETED
                    previous_result = result or {}

                    logger.info(f"✅ Saga {self.saga_id}: Krok {step.name} zakończony pomyślnie")

                except Exception as e:
                    step.status = SagaStatus.FAILED
                    step.error = str(e)
                    logger.error(f"❌ Saga {self.saga_id}: Błąd w kroku {step.name}: {e}")

                    # Kompensacja
                    self._compensate(i)
                    self.status = SagaStatus.COMPENSATED
                    if self.saga_log:
                        self.saga_log.status = SagaStatus.COMPENSATED.value
                        self.saga_log.completed_at = timezone.now()
                        self.saga_log.error_message = str(e)
                        self.saga_log.save(using='matterhorn1')

                    return SagaResult(
                        saga_id=self.saga_id,
                        status=SagaStatus.COMPENSATED,
                        steps=self.steps,
                        error=str(e),
                        created_at=self.created_at,
                        completed_at=timezone.now()
                    )

            self.status = SagaStatus.COMPLETED
            if self.saga_log:
                self.saga_log.status = SagaStatus.COMPLETED.value
                self.saga_log.completed_at = timezone.now()
                self.saga_log.completed_steps = len(self.steps)
                self.saga_log.save(using='matterhorn1')

            return SagaResult(
                saga_id=self.saga_id,
                status=SagaStatus.COMPLETED,
                steps=self.steps,
                created_at=self.created_at,
                completed_at=timezone.now()
            )

        except Exception as e:
            self.status = SagaStatus.FAILED
            self.error = str(e)
            if self.saga_log:
                self.saga_log.status = SagaStatus.FAILED.value
                self.saga_log.completed_at = timezone.now()
                self.saga_log.error_message = str(e)
                self.saga_log.save(using='matterhorn1')

            return SagaResult(
                saga_id=self.saga_id,
                status=SagaStatus.FAILED,
                steps=self.steps,
                error=str(e),
                created_at=self.created_at,
                completed_at=timezone.now()
            )

    def _compensate(self, failed_step_index: int):
        """Wykonaj kompensację dla wszystkich wykonanych kroków"""
        logger.info(f"🔄 Saga {self.saga_id}: Rozpoczynam kompensację")
        self.status = SagaStatus.COMPENSATING

        for i in range(failed_step_index - 1, -1, -1):
            step = self.steps[i]
            if step.status == SagaStatus.COMPLETED:
                try:
                    logger.info(f"🔄 Saga {self.saga_id}: Kompensuję krok {step.name}")
                    step.compensate_func(step.data, step.result)
                    step.compensated_at = timezone.now()
                    logger.info(f"✅ Saga {self.saga_id}: Kompensacja kroku {step.name} zakończona")
                except Exception as e:
                    logger.error(f"❌ Saga {self.saga_id}: Błąd kompensacji kroku {step.name}: {e}")


class SagaService:
    """
    Serwis do zarządzania Saga dla WEGA
    """

    @staticmethod
    def create_product_with_mapping(wega_product_data: Dict, mpd_product_data: Dict) -> SagaResult:
        """
        Utwórz produkt w wega i MPD z automatyczną kompensacją
        """
        saga = SagaOrchestrator(saga_type="wega_product_creation")

        # Krok 1: Utwórz produkt w MPD
        saga.add_step(
            name="create_mpd_product",
            execute_func=SagaService._create_mpd_product,
            compensate_func=SagaService._delete_mpd_product,
            data={"mpd_data": mpd_product_data}
        )

        # Krok 2: Utwórz produkt w wega z mapping
        saga.add_step(
            name="create_wega_product_with_mapping",
            execute_func=SagaService._create_wega_product_with_mapping,
            compensate_func=SagaService._delete_wega_product_mapping,
            data={
                "wega_data": wega_product_data,
                "mpd_product_id": None
            }
        )

        # Krok 3: Dodaj atrybuty w MPD
        saga.add_step(
            name="add_mpd_attributes",
            execute_func=SagaService._add_mpd_attributes,
            compensate_func=SagaService._remove_mpd_attributes,
            data={
                "mpd_product_id": None,
                "attributes": mpd_product_data.get("attributes", [])
            }
        )

        # Krok 4: Dodaj ścieżki w MPD (jeśli podano)
        if mpd_product_data.get("paths"):
            saga.add_step(
                name="add_mpd_paths",
                execute_func=SagaService._add_mpd_paths,
                compensate_func=SagaService._remove_mpd_paths,
                data={
                    "mpd_product_id": None,
                    "paths": mpd_product_data.get("paths", [])
                }
            )

        # Krok 5: Dodaj skład materiałowy (jeśli podano)
        if mpd_product_data.get("fabric"):
            saga.add_step(
                name="add_mpd_fabric",
                execute_func=SagaService._add_mpd_fabric,
                compensate_func=SagaService._remove_mpd_fabric,
                data={
                    "mpd_product_id": None,
                    "fabric": mpd_product_data.get("fabric", [])
                }
            )

        # Krok 6: Utwórz warianty w MPD (jeśli podano size_category)
        if mpd_product_data.get("size_category"):
            saga.add_step(
                name="create_mpd_variants",
                execute_func=SagaService._create_mpd_product_variants,
                compensate_func=SagaService._delete_mpd_product_variants,
                data={
                    "mpd_product_id": None,
                    "wega_product_id": wega_product_data.get("product_id"),
                    "size_category": mpd_product_data.get("size_category"),
                    "producer_code": mpd_product_data.get("producer_code"),
                    "main_color_id": mpd_product_data.get("main_color_id"),
                    "producer_color_name": mpd_product_data.get("producer_color_name")
                }
            )

        # Krok 7: Upload zdjęć do bucketa
        saga.add_step(
            name="upload_product_images",
            execute_func=SagaService._upload_product_images,
            compensate_func=SagaService._remove_product_images,
            data={
                "mpd_product_id": None,
                "wega_product_id": wega_product_data.get("product_id"),
                "producer_color_name": mpd_product_data.get("producer_color_name")
            }
        )

        return saga.execute()

    @staticmethod
    def _create_mpd_product(mpd_data: Dict) -> Dict:
        """Utwórz produkt w MPD"""
        from MPD.models import Products, Brands, ProductSeries

        logger.info(f"🔄 Tworzę produkt w MPD: {mpd_data.get('name', 'Unknown')}")

        try:
            brand_id = None
            brand_name = mpd_data.get('brand_name')
            if brand_name:
                brand, _ = Brands.objects.using('MPD').get_or_create(name=brand_name)
                brand_id = brand.id

            series_id = None
            series_name = mpd_data.get('series_name')
            if series_name:
                series, _ = ProductSeries.objects.using('MPD').get_or_create(name=series_name)
                series_id = series.id

            product = Products.objects.using('MPD').create(
                name=mpd_data.get('name'),
                description=mpd_data.get('description', ''),
                short_description=mpd_data.get('short_description', ''),
                brand_id=brand_id,
                unit_id=mpd_data.get('unit_id'),
                series_id=series_id,
                visibility=mpd_data.get('visibility', False)
            )

            mpd_product_id = product.id
            logger.info(f"✅ Utworzono produkt w MPD z ID: {mpd_product_id}")

            return {
                'mpd_product_id': mpd_product_id,
                'created_products': [{'id': mpd_product_id, 'name': product.name}]
            }

        except Exception as e:
            logger.error(f"❌ Błąd podczas tworzenia produktu w MPD: {e}")
            raise Exception(f"Failed to create MPD product: {e}")

    @staticmethod
    def _delete_mpd_product(mpd_data: Dict, mpd_product_id: int = None) -> Dict:
        """Usuń produkt z MPD (kompensacja)"""
        if not mpd_product_id:
            logger.warning("⚠️ Brak mpd_product_id do usunięcia")
            return {}

        logger.info(f"🔄 Usuwam produkt z MPD: {mpd_product_id}")

        try:
            from django.conf import settings
            import requests

            mpd_api_url = f"{settings.MPD_API_URL}/products/{mpd_product_id}/"
            response = requests.delete(mpd_api_url, timeout=120)

            if response.status_code == 200:
                logger.info(f"✅ Usunięto produkt z MPD: {mpd_product_id}")
            else:
                logger.warning(f"⚠️ Nie udało się usunąć produktu z MPD: {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania produktu z MPD: {e}")

        return {}

    @staticmethod
    def _create_wega_product_with_mapping(wega_data: Dict, mpd_product_id: int = None) -> Dict:
        """Utwórz/zaktualizuj produkt w wega z mapping"""
        from wega.models import Product

        logger.info(f"🔄 Aktualizuję mapping produktu w wega: {mpd_product_id}")

        try:
            product = Product.objects.get(id=wega_data['product_id'])
            product.mapped_product_uid = mpd_product_id
            product.is_mapped = True
            product.save()

            logger.info(f"✅ Zaktualizowano mapping produktu {product.id} -> MPD {mpd_product_id}")

        except Product.DoesNotExist:
            raise Exception(f"Product {wega_data['product_id']} not found in wega")

        return {"wega_product_id": wega_data['product_id']}

    @staticmethod
    def _delete_wega_product_mapping(wega_data: Dict) -> Dict:
        """Usuń mapping produktu w wega (kompensacja)"""
        from wega.models import Product

        logger.info(f"🔄 Usuwam mapping produktu w wega: {wega_data['product_id']}")

        try:
            product = Product.objects.get(id=wega_data['product_id'])
            product.mapped_product_uid = None
            product.is_mapped = False
            product.save()

            logger.info(f"✅ Usunięto mapping produktu {product.id}")

        except Product.DoesNotExist:
            logger.warning(f"⚠️ Produkt {wega_data['product_id']} nie istnieje w wega")

        return {}

    @staticmethod
    def _add_mpd_attributes(mpd_product_id: int, attributes: List[int]) -> Dict:
        """Dodaj atrybuty do produktu w MPD"""
        logger.info(f"🔄 Dodaję atrybuty do produktu MPD {mpd_product_id}: {attributes}")

        if not attributes:
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for attribute_id in attributes:
                    cursor.execute(
                        "INSERT INTO product_attributes (product_id, attribute_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [mpd_product_id, attribute_id]
                    )

            logger.info(f"✅ Dodano {len(attributes)} atrybutów do produktu MPD {mpd_product_id}")

        except Exception as e:
            raise Exception(f"Failed to add attributes to MPD product: {e}")

        return {"added_attributes": len(attributes)}

    @staticmethod
    def _remove_mpd_attributes(mpd_product_id: int, attributes: List[int]) -> Dict:
        """Usuń atrybuty z produktu w MPD (kompensacja)"""
        logger.info(f"🔄 Usuwam atrybuty z produktu MPD {mpd_product_id}")

        try:
            with connections['MPD'].cursor() as cursor:
                for attribute_id in attributes:
                    cursor.execute(
                        "DELETE FROM product_attributes WHERE product_id = %s AND attribute_id = %s",
                        [mpd_product_id, attribute_id]
                    )
        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania atrybutów: {e}")

        return {}

    @staticmethod
    def _add_mpd_paths(mpd_product_id: int, paths: List[int]) -> Dict:
        """Dodaj ścieżki do produktu w MPD"""
        logger.info(f"🔄 Dodaję ścieżki do produktu MPD {mpd_product_id}: {paths}")

        if not paths:
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for path_id in paths:
                    cursor.execute(
                        "INSERT INTO product_path (product_id, path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [mpd_product_id, path_id]
                    )

            logger.info(f"✅ Dodano {len(paths)} ścieżek do produktu MPD {mpd_product_id}")

        except Exception as e:
            raise Exception(f"Failed to add paths to MPD product: {e}")

        return {"added_paths": len(paths)}

    @staticmethod
    def _remove_mpd_paths(mpd_product_id: int, paths: List[int]) -> Dict:
        """Usuń ścieżki z produktu w MPD (kompensacja)"""
        logger.info(f"🔄 Usuwam ścieżki z produktu MPD {mpd_product_id}")

        try:
            with connections['MPD'].cursor() as cursor:
                for path_id in paths:
                    cursor.execute(
                        "DELETE FROM product_path WHERE product_id = %s AND path_id = %s",
                        [mpd_product_id, path_id]
                    )
        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania ścieżek: {e}")

        return {}

    @staticmethod
    def _add_mpd_fabric(mpd_product_id: int, fabric: List[Dict]) -> Dict:
        """Dodaj skład materiałowy do produktu w MPD"""
        logger.info(f"🔄 Dodaję skład materiałowy do produktu MPD {mpd_product_id}")

        if not fabric:
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for fabric_item in fabric:
                    cursor.execute("""
                        INSERT INTO product_fabric (product_id, fabric_component_id, percentage)
                        VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
                    """, [mpd_product_id, fabric_item['component_id'], fabric_item['percentage']])

            logger.info(f"✅ Dodano skład materiałowy do produktu MPD {mpd_product_id}")

        except Exception as e:
            raise Exception(f"Failed to add fabric to MPD product: {e}")

        return {"added_fabric": len(fabric)}

    @staticmethod
    def _remove_mpd_fabric(mpd_product_id: int, fabric: List[Dict]) -> Dict:
        """Usuń skład materiałowy z produktu w MPD (kompensacja)"""
        logger.info(f"🔄 Usuwam skład materiałowy z produktu MPD {mpd_product_id}")

        try:
            with connections['MPD'].cursor() as cursor:
                for fabric_item in fabric:
                    cursor.execute("""
                        DELETE FROM product_fabric 
                        WHERE product_id = %s AND fabric_component_id = %s
                    """, [mpd_product_id, fabric_item['component_id']])
        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania składu materiałowego: {e}")

        return {}

    @staticmethod
    def _create_mpd_product_variants(data: Dict) -> Dict:
        """Utwórz warianty w MPD"""
        from wega.saga_variants import create_mpd_variants

        mpd_product_id = data.get('mpd_product_id')
        wega_product_id = data.get('wega_product_id')
        size_category = data.get('size_category')
        producer_code = data.get('producer_code')
        main_color_id = data.get('main_color_id')
        producer_color_name = data.get('producer_color_name')

        logger.info(f"🔄 Tworzę warianty w MPD dla produktu {mpd_product_id}")

        try:
            result = create_mpd_variants(
                mpd_product_id, wega_product_id, size_category,
                producer_code, main_color_id, producer_color_name
            )
            return result
        except Exception as e:
            raise Exception(f"Failed to create MPD variants: {e}")

    @staticmethod
    def _delete_mpd_product_variants(data: Dict) -> Dict:
        """Usuń warianty z MPD (kompensacja)"""
        mpd_product_id = data.get('mpd_product_id')
        logger.info(f"🔄 Usuwam warianty z MPD dla produktu {mpd_product_id}")

        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute(
                    "DELETE FROM product_variants WHERE product_id = %s",
                    [mpd_product_id]
                )
        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania wariantów: {e}")

        return {}

    @staticmethod
    def _upload_product_images(data: Dict) -> Dict:
        """Upload zdjęć produktu do bucketa"""
        mpd_product_id = data.get('mpd_product_id')
        wega_product_id = data.get('wega_product_id')
        producer_color_name = data.get('producer_color_name')

        logger.info(f"🔄 Uploaduję zdjęcia dla produktu MPD {mpd_product_id}")

        try:
            from wega.models import Product, ProductImage
            product = Product.objects.get(id=wega_product_id)
            
            uploaded_count = 0
            for image in product.images.all():
                # Tutaj logika uploadu do bucketa
                # Na razie tylko logujemy
                logger.info(f"Upload obrazu: {image.url}")
                uploaded_count += 1

            return {"uploaded_images": uploaded_count}
        except Exception as e:
            logger.error(f"❌ Błąd podczas uploadu zdjęć: {e}")
            return {"uploaded_images": 0, "error": str(e)}

    @staticmethod
    def _remove_product_images(data: Dict) -> Dict:
        """Usuń zdjęcia z bucketa (kompensacja)"""
        logger.info(f"🔄 Usuwam zdjęcia z bucketa")
        return {}

