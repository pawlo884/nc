"""
Saga Pattern Implementation for Cross-Database Operations

Ten moduł implementuje Saga Pattern do bezpiecznego wykonywania operacji
między różnymi bazami danych (matterhorn1, MPD) z automatyczną kompensacją.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass
from django.db import connections
from django.utils import timezone
from . import saga_variants
from .defs_db import resolve_image_url

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
class SagaStep:
    """Pojedynczy krok w Saga"""
    name: str
    execute_func: Callable
    compensate_func: Callable
    data: Dict[str, Any] = None
    status: SagaStatus = SagaStatus.PENDING
    error: Optional[str] = None
    executed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None  # Wynik wykonania kroku


@dataclass
class SagaResult:
    """Wynik wykonania Saga"""
    saga_id: str
    status: SagaStatus
    steps: List[SagaStep]
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None


class SagaOrchestrator:
    """
    Orchestrator dla Saga Pattern

    Zarządza wykonywaniem kroków i kompensacją w przypadku błędów.
    """

    def __init__(self, saga_id: str = None, saga_type: str = "generic", enable_logging: bool = True):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.saga_type = saga_type
        self.enable_logging = enable_logging
        self.steps: List[SagaStep] = []
        self.status = SagaStatus.PENDING
        self.created_at = timezone.now()
        self.error = None
        self.saga_log = None

        # Utwórz log w bazie danych jeśli logging jest włączony
        if self.enable_logging:
            self._create_saga_log()

    def add_step(self, name: str, execute_func: Callable, compensate_func: Callable, data: Dict[str, Any] = None):
        """Dodaj krok do Saga"""
        step = SagaStep(
            name=name,
            execute_func=execute_func,
            compensate_func=compensate_func,
            data=data or {}
        )
        self.steps.append(step)
        logger.info(f"🔄 Saga {self.saga_id}: Dodano krok '{name}'")

        # Utwórz log kroku w bazie danych
        if self.enable_logging and self.saga_log:
            self._create_step_log(step)

        return self

    def _create_saga_log(self):
        """Utwórz log Saga w bazie danych"""
        try:
            from matterhorn1.models import Saga
            self.saga_log = Saga.objects.using('matterhorn1').create(
                saga_id=self.saga_id,
                saga_type=self.saga_type,
                status=SagaStatus.PENDING.value,
                input_data={}
            )
            logger.info(f"📝 Saga {self.saga_id}: Utworzono log w bazie danych")
        except Exception as e:
            logger.warning(
                f"⚠️ Saga {self.saga_id}: Nie udało się utworzyć logu: {e}")
            self.enable_logging = False

    def _create_step_log(self, step: SagaStep):
        """Utwórz log kroku w bazie danych"""
        try:
            from matterhorn1.models import SagaStep as SagaStepModel
            SagaStepModel.objects.using('matterhorn1').create(
                saga=self.saga_log,
                step_name=step.name,
                step_order=len(self.steps),
                status=SagaStatus.PENDING.value,
                input_data=step.data or {}
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Saga {self.saga_id}: Nie udało się utworzyć logu kroku '{step.name}': {e}")

    def _update_saga_log(self, status: SagaStatus, error: str = None):
        """Aktualizuj log Saga w bazie danych"""
        if not self.enable_logging or not self.saga_log:
            return

        try:
            self.saga_log.status = status.value
            if error:
                self.saga_log.error_message = error
            if status == SagaStatus.RUNNING:
                self.saga_log.started_at = timezone.now()
            elif status in [SagaStatus.COMPLETED, SagaStatus.COMPENSATED]:
                self.saga_log.completed_at = timezone.now()
            self.saga_log.save()
        except Exception as e:
            logger.warning(
                f"⚠️ Saga {self.saga_id}: Nie udało się zaktualizować logu: {e}")

    def _update_step_log(self, step: SagaStep, status: SagaStatus, error: str = None, output_data: Dict = None):
        """Aktualizuj log kroku w bazie danych"""
        if not self.enable_logging or not self.saga_log:
            return

        try:
            from matterhorn1.models import SagaStep as SagaStepModel
            step_log = SagaStepModel.objects.using('matterhorn1').get(
                saga=self.saga_log,
                step_name=step.name
            )
            step_log.status = status.value
            if error:
                step_log.error_message = error
            if output_data:
                step_log.output_data = output_data
            if status == SagaStatus.RUNNING:
                step_log.started_at = timezone.now()
            elif status == SagaStatus.COMPLETED:
                step_log.completed_at = timezone.now()
            elif status == SagaStatus.COMPENSATED:
                step_log.compensated_at = timezone.now()
                step_log.compensation_attempted = True
                step_log.compensation_successful = True
            step_log.save()
        except Exception as e:
            logger.warning(
                f"⚠️ Saga {self.saga_id}: Nie udało się zaktualizować logu kroku '{step.name}': {e}")

    def execute(self) -> SagaResult:
        """
        Wykonaj wszystkie kroki Saga

        Jeśli któryś krok się nie powiedzie, wykonaj kompensację
        dla wszystkich poprzednich kroków w odwrotnej kolejności.
        """
        logger.info(
            f"🚀 Saga {self.saga_id}: Rozpoczynam wykonanie {len(self.steps)} kroków")
        self.status = SagaStatus.RUNNING
        self._update_saga_log(self.status)

        try:
            # Wykonaj wszystkie kroki
            for i, step in enumerate(self.steps):
                result = self._execute_step(step)
                step.result = result

                # Aktualizuj dane następnych kroków z wynikiem bieżącego
                if result and i < len(self.steps) - 1:
                    for next_step in self.steps[i + 1:]:
                        # Aktualizuj wartości None w danych następnych kroków
                        for key, value in result.items():
                            if key in next_step.data and next_step.data[key] is None:
                                next_step.data[key] = value
                                logger.info(
                                    f"🔄 Saga {self.saga_id}: Przekazuję {key}={value} do kroku '{next_step.name}'")

            # Wszystkie kroki wykonane pomyślnie
            self.status = SagaStatus.COMPLETED
            self._update_saga_log(self.status)
            logger.info(
                f"✅ Saga {self.saga_id}: Wszystkie kroki wykonane pomyślnie")

        except Exception as e:
            # Błąd podczas wykonywania - wykonaj kompensację
            logger.error(
                f"❌ Saga {self.saga_id}: Błąd podczas wykonywania: {e}")
            self.error = str(e)
            self._update_saga_log(self.status, str(e))
            self._compensate()

        return self._create_result()

    def _execute_step(self, step: SagaStep):
        """Wykonaj pojedynczy krok"""
        logger.info(f"🔄 Saga {self.saga_id}: Wykonuję krok '{step.name}'")
        step.status = SagaStatus.RUNNING
        self._update_step_log(step, step.status)

        try:
            # Wykonaj funkcję kroku
            result = step.execute_func(**step.data)
            step.status = SagaStatus.COMPLETED
            step.executed_at = timezone.now()
            self._update_step_log(step, step.status, output_data=result)

            logger.info(
                f"✅ Saga {self.saga_id}: Krok '{step.name}' wykonany pomyślnie")
            return result

        except Exception as e:
            step.status = SagaStatus.FAILED
            step.error = str(e)
            self._update_step_log(step, step.status, str(e))
            logger.error(
                f"❌ Saga {self.saga_id}: Błąd w kroku '{step.name}': {e}")
            raise e

    def _compensate(self):
        """Wykonaj kompensację dla wszystkich wykonanych kroków"""
        logger.info(f"🔄 Saga {self.saga_id}: Rozpoczynam kompensację")
        self.status = SagaStatus.COMPENSATING
        self._update_saga_log(self.status)

        # Wykonaj kompensację w odwrotnej kolejności
        executed_steps = [
            step for step in self.steps if step.status == SagaStatus.COMPLETED]

        for step in reversed(executed_steps):
            try:
                logger.info(
                    f"🔄 Saga {self.saga_id}: Kompensuję krok '{step.name}'")
                step.compensate_func(**step.data)
                step.compensated_at = timezone.now()
                self._update_step_log(step, SagaStatus.COMPENSATED)
                logger.info(
                    f"✅ Saga {self.saga_id}: Krok '{step.name}' skompensowany")

            except Exception as e:
                logger.error(
                    f"❌ Saga {self.saga_id}: Błąd kompensacji kroku '{step.name}': {e}")
                self._update_step_log(step, SagaStatus.FAILED, str(e))
                # Kontynuuj kompensację innych kroków

        self.status = SagaStatus.COMPENSATED
        self._update_saga_log(self.status)
        logger.info(f"✅ Saga {self.saga_id}: Kompensacja zakończona")

    def _create_result(self) -> SagaResult:
        """Utwórz wynik Saga"""
        return SagaResult(
            saga_id=self.saga_id,
            status=self.status,
            steps=self.steps.copy(),
            error=self.error,
            created_at=self.created_at,
            completed_at=datetime.now() if self.status in [
                SagaStatus.COMPLETED, SagaStatus.COMPENSATED] else None
        )


class SagaService:
    """
    Serwis do zarządzania Saga

    Umożliwia wykonywanie typowych operacji cross-database
    używając Saga Pattern.
    """

    @staticmethod
    def create_product_with_mapping(matterhorn_product_data: Dict, mpd_product_data: Dict) -> SagaResult:
        """
        Utwórz produkt w matterhorn1 i MPD z automatyczną kompensacją

        Args:
            matterhorn_product_data: Dane produktu dla matterhorn1
            mpd_product_data: Dane produktu dla MPD

        Returns:
            SagaResult: Wynik operacji
        """
        saga = SagaOrchestrator(saga_type="product_creation")

        # Krok 1: Utwórz produkt w MPD
        saga.add_step(
            name="create_mpd_product",
            execute_func=SagaService._create_mpd_product,
            compensate_func=SagaService._delete_mpd_product,
            data={"mpd_data": mpd_product_data}
        )

        # Krok 2: Utwórz produkt w matterhorn1 z mapping
        saga.add_step(
            name="create_matterhorn_product_with_mapping",
            execute_func=SagaService._create_matterhorn_product_with_mapping,
            compensate_func=SagaService._delete_matterhorn_product_mapping,
            data={
                "matterhorn_data": matterhorn_product_data,
                "mpd_product_id": None  # Będzie wypełnione przez poprzedni krok
            }
        )

        # Krok 3: Dodaj atrybuty w MPD
        saga.add_step(
            name="add_mpd_attributes",
            execute_func=SagaService._add_mpd_attributes,
            compensate_func=SagaService._remove_mpd_attributes,
            data={
                "mpd_product_id": None,  # Będzie wypełnione przez poprzedni krok
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
                    "mpd_product_id": None,  # Będzie wypełnione przez poprzedni krok
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
                    "mpd_product_id": None,  # Będzie wypełnione przez poprzedni krok
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
                    "mpd_product_id": None,  # Będzie wypełnione przez poprzedni krok
                    "matterhorn_product_id": matterhorn_product_data.get("product_id"),
                    "size_category": mpd_product_data.get("size_category"),
                    "producer_code": mpd_product_data.get("producer_code"),
                    "main_color_id": mpd_product_data.get("main_color_id"),
                    "producer_color_name": mpd_product_data.get("producer_color_name")
                }
            )

        # Krok 7: Upload zdjęć do bucketa (jeśli produkt ma zdjęcia)
        saga.add_step(
            name="upload_product_images",
            execute_func=SagaService._upload_product_images,
            compensate_func=SagaService._remove_product_images,
            data={
                "mpd_product_id": None,  # Będzie wypełnione przez poprzedni krok
                "matterhorn_product_id": matterhorn_product_data.get("product_id"),
                "producer_color_name": mpd_product_data.get("producer_color_name")
            }
        )

        return saga.execute()

    @staticmethod
    def create_variants_with_mapping(product_id: int, mpd_product_id: int, variants_data: List[Dict]) -> SagaResult:
        """
        Utwórz warianty w MPD i zaktualizuj mapping w matterhorn1

        Args:
            product_id: ID produktu w matterhorn1
            mpd_product_id: ID produktu w MPD
            variants_data: Lista danych wariantów

        Returns:
            SagaResult: Wynik operacji
        """
        saga = SagaOrchestrator(saga_type="variant_creation")

        # Krok 1: Utwórz warianty w MPD
        saga.add_step(
            name="create_mpd_variants",
            execute_func=SagaService._create_mpd_variants,
            compensate_func=SagaService._delete_mpd_variants,
            data={
                "mpd_product_id": mpd_product_id,
                "variants_data": variants_data
            }
        )

        # Krok 2: Zaktualizuj mapping w matterhorn1
        saga.add_step(
            name="update_matterhorn_variants_mapping",
            execute_func=SagaService._update_matterhorn_variants_mapping,
            compensate_func=SagaService._revert_matterhorn_variants_mapping,
            data={
                "product_id": product_id,
                "variants_data": variants_data
            }
        )

        return saga.execute()

    # Implementacje funkcji kroków

    @staticmethod
    def _create_mpd_product(mpd_data: Dict) -> Dict:
        """Utwórz produkt w MPD bezpośrednio przez model Django"""
        from django.db import connections
        from MPD.models import Products, Brands, ProductSeries

        logger.info(
            f"🔄 Tworzę produkt w MPD: {mpd_data.get('name', 'Unknown')}")

        try:
            # Pobierz lub utwórz markę
            brand_id = None
            brand_name = mpd_data.get('brand_name')
            if brand_name:
                brand, _ = Brands.objects.using(
                    'MPD').get_or_create(name=brand_name)
                brand_id = brand.id

            # Pobierz lub utwórz series
            series_id = None
            series_name = mpd_data.get('series_name')
            if series_name:
                series, _ = ProductSeries.objects.using(
                    'MPD').get_or_create(name=series_name)
                series_id = series.id

            # Utwórz produkt w MPD
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

            # Wyślij żądanie usunięcia do API MPD
            mpd_api_url = f"{settings.MPD_API_URL}/products/{mpd_product_id}/"
            response = requests.delete(mpd_api_url, timeout=120)

            if response.status_code == 200:
                logger.info(f"✅ Usunięto produkt z MPD: {mpd_product_id}")
            else:
                logger.warning(
                    f"⚠️ Nie udało się usunąć produktu z MPD: {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania produktu z MPD: {e}")

        return {}

    @staticmethod
    def _create_matterhorn_product_with_mapping(matterhorn_data: Dict, mpd_product_id: int = None) -> Dict:
        """Utwórz/zaktualizuj produkt w matterhorn1 z mapping"""
        from matterhorn1.models import Product

        logger.info(
            f"🔄 Aktualizuję mapping produktu w matterhorn1: {mpd_product_id}")

        try:
            product = Product.objects.get(id=matterhorn_data['product_id'])
            product.mapped_product_uid = mpd_product_id
            product.is_mapped = True
            product.save()

            logger.info(
                f"✅ Zaktualizowano mapping produktu {product.id} -> MPD {mpd_product_id}")

        except Product.DoesNotExist:
            raise Exception(
                f"Product {matterhorn_data['product_id']} not found in matterhorn1")

        return {"matterhorn_product_id": matterhorn_data['product_id']}

    @staticmethod
    def _delete_matterhorn_product_mapping(matterhorn_data: Dict, **kwargs) -> Dict:
        """Usuń mapping produktu w matterhorn1 (kompensacja). kwargs (np. mpd_product_id) ignorowane."""
        from matterhorn1.models import Product

        logger.info(
            f"🔄 Usuwam mapping produktu w matterhorn1: {matterhorn_data['product_id']}")

        try:
            product = Product.objects.get(id=matterhorn_data['product_id'])
            product.mapped_product_uid = None
            product.is_mapped = False
            product.save()

            logger.info(f"✅ Usunięto mapping produktu {product.id}")

        except Product.DoesNotExist:
            logger.warning(
                f"⚠️ Produkt {matterhorn_data['product_id']} nie istnieje w matterhorn1")

        return {}

    @staticmethod
    def _add_mpd_attributes(mpd_product_id: int, attributes: List[int]) -> Dict:
        """Dodaj atrybuty do produktu w MPD"""
        logger.info(
            f"🔄 Dodaję atrybuty do produktu MPD {mpd_product_id}: {attributes}")

        if not attributes:
            logger.info("ℹ️ Brak atrybutów do dodania")
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for attribute_id in attributes:
                    cursor.execute(
                        "INSERT INTO product_attributes (product_id, attribute_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [mpd_product_id, attribute_id]
                    )

            logger.info(
                f"✅ Dodano {len(attributes)} atrybutów do produktu MPD {mpd_product_id}")

        except Exception as e:
            raise Exception(f"Failed to add attributes to MPD product: {e}")

        return {"added_attributes": len(attributes)}

    @staticmethod
    def _remove_mpd_attributes(mpd_product_id: int, attributes: List[int]) -> Dict:
        """Usuń atrybuty z produktu w MPD (kompensacja)"""
        logger.info(
            f"🔄 Usuwam atrybuty z produktu MPD {mpd_product_id}: {attributes}")

        if not attributes:
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for attribute_id in attributes:
                    cursor.execute(
                        "DELETE FROM product_attributes WHERE product_id = %s AND attribute_id = %s",
                        [mpd_product_id, attribute_id]
                    )

            logger.info(
                f"✅ Usunięto {len(attributes)} atrybutów z produktu MPD {mpd_product_id}")

        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania atrybutów: {e}")

        return {}

    @staticmethod
    def _create_mpd_variants(mpd_product_id: int, variants_data: List[Dict]) -> Dict:
        """Utwórz warianty w MPD"""
        logger.info(
            f"🔄 Tworzę {len(variants_data)} wariantów w MPD dla produktu {mpd_product_id}")

        created_variants = []

        try:
            with connections['MPD'].cursor() as cursor:
                for variant_data in variants_data:
                    cursor.execute("""
                        INSERT INTO product_variants 
                        (variant_id, product_id, color_id, size_id, iai_product_id, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        RETURNING variant_id
                    """, [
                        variant_data['variant_id'],
                        mpd_product_id,
                        variant_data['color_id'],
                        variant_data['size_id'],
                        variant_data.get('iai_product_id')
                    ])

                    result = cursor.fetchone()
                    if result:
                        created_variants.append(result[0])

            logger.info(f"✅ Utworzono {len(created_variants)} wariantów w MPD")

        except Exception as e:
            raise Exception(f"Failed to create MPD variants: {e}")

        return {"created_variants": created_variants}

    @staticmethod
    def _delete_mpd_variants(mpd_product_id: int, variants_data: List[Dict], created_variants: List[int] = None) -> Dict:
        """Usuń warianty z MPD (kompensacja)"""
        logger.info(f"🔄 Usuwam warianty z MPD dla produktu {mpd_product_id}")

        if not created_variants:
            logger.warning("⚠️ Brak wariantów do usunięcia")
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for variant_id in created_variants:
                    cursor.execute(
                        "DELETE FROM product_variants WHERE variant_id = %s", [variant_id])

            logger.info(f"✅ Usunięto {len(created_variants)} wariantów z MPD")

        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania wariantów: {e}")

        return {}

    @staticmethod
    def _update_matterhorn_variants_mapping(product_id: int, variants_data: List[Dict]) -> Dict:
        """Zaktualizuj mapping wariantów w matterhorn1"""
        logger.info(
            f"🔄 Aktualizuję mapping wariantów w matterhorn1 dla produktu {product_id}")

        try:
            with connections['matterhorn1'].cursor() as cursor:
                for variant_data in variants_data:
                    cursor.execute("""
                        UPDATE productvariant 
                        SET mapped_variant_uid = %s, is_mapped = true, updated_at = NOW() 
                        WHERE variant_uid = %s
                    """, [variant_data['variant_id'], variant_data['variant_uid']])

            logger.info(
                f"✅ Zaktualizowano mapping {len(variants_data)} wariantów w matterhorn1")

        except Exception as e:
            raise Exception(
                f"Failed to update matterhorn variants mapping: {e}")

        return {"updated_variants": len(variants_data)}

    @staticmethod
    def _revert_matterhorn_variants_mapping(product_id: int, variants_data: List[Dict]) -> Dict:
        """Cofnij mapping wariantów w matterhorn1 (kompensacja)"""
        logger.info(
            f"🔄 Cofam mapping wariantów w matterhorn1 dla produktu {product_id}")

        try:
            with connections['matterhorn1'].cursor() as cursor:
                for variant_data in variants_data:
                    cursor.execute("""
                        UPDATE productvariant 
                        SET mapped_variant_uid = NULL, is_mapped = false, updated_at = NOW() 
                        WHERE variant_uid = %s
                    """, [variant_data['variant_uid']])

            logger.info(
                f"✅ Cofnięto mapping {len(variants_data)} wariantów w matterhorn1")

        except Exception as e:
            logger.error(f"❌ Błąd podczas cofania mapping wariantów: {e}")

        return {}

    @staticmethod
    def _add_mpd_paths(mpd_product_id: int, paths: List[int]) -> Dict:
        """Dodaj ścieżki do produktu w MPD"""
        logger.info(
            f"🔄 Dodaję ścieżki do produktu MPD {mpd_product_id}: {paths}")

        if not paths:
            logger.info("ℹ️ Brak ścieżek do dodania")
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for path_id in paths:
                    cursor.execute(
                        "INSERT INTO product_path (product_id, path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [mpd_product_id, path_id]
                    )

            logger.info(
                f"✅ Dodano {len(paths)} ścieżek do produktu MPD {mpd_product_id}")

        except Exception as e:
            raise Exception(f"Failed to add paths to MPD product: {e}")

        return {"added_paths": len(paths)}

    @staticmethod
    def _remove_mpd_paths(mpd_product_id: int, paths: List[int]) -> Dict:
        """Usuń ścieżki z produktu w MPD (kompensacja)"""
        logger.info(
            f"🔄 Usuwam ścieżki z produktu MPD {mpd_product_id}: {paths}")

        if not paths:
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                for path_id in paths:
                    cursor.execute(
                        "DELETE FROM product_path WHERE product_id = %s AND path_id = %s",
                        [mpd_product_id, path_id]
                    )

            logger.info(
                f"✅ Usunięto {len(paths)} ścieżek z produktu MPD {mpd_product_id}")

        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania ścieżek: {e}")

        return {}

    @staticmethod
    def _add_mpd_fabric(mpd_product_id: int, fabric: List[Dict]) -> Dict:
        """Dodaj skład materiałowy do produktu w MPD"""
        logger.info(
            f"🔄 Dodaję skład materiałowy do produktu MPD {mpd_product_id}: {len(fabric)} komponentów")

        if not fabric:
            logger.info("ℹ️ Brak składu do dodania")
            return {}

        try:
            # Sprawdź czy suma procentów jest poprawna
            total_percentage = sum(item['percentage'] for item in fabric)

            if total_percentage > 100:
                logger.warning(
                    f"Suma procentów materiałów przekracza 100%: {total_percentage}%. Pomijam zapis.")
                return {"error": "Suma procentów przekracza 100%"}

            if total_percentage == 0:
                logger.info("Brak poprawnych procentów materiałów do zapisu.")
                return {}

            with connections['MPD'].cursor() as cursor:
                for item in fabric:
                    component_id = item['component_id']
                    percentage = item['percentage']

                    if percentage > 0 and percentage <= 100:
                        cursor.execute(
                            "INSERT INTO product_fabric (product_id, component_id, percentage) VALUES (%s, %s, %s)",
                            [mpd_product_id, component_id, percentage]
                        )

            logger.info(
                f"✅ Dodano {len(fabric)} komponentów składu do produktu MPD {mpd_product_id}")

        except Exception as e:
            raise Exception(f"Failed to add fabric to MPD product: {e}")

        return {"added_fabric": len(fabric)}

    @staticmethod
    def _remove_mpd_fabric(mpd_product_id: int, fabric: List[Dict]) -> Dict:
        """Usuń skład materiałowy z produktu w MPD (kompensacja)"""
        logger.info(
            f"🔄 Usuwam skład materiałowy z produktu MPD {mpd_product_id}")

        if not fabric:
            return {}

        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute(
                    "DELETE FROM product_fabric WHERE product_id = %s",
                    [mpd_product_id]
                )

            logger.info(
                f"✅ Usunięto skład materiałowy z produktu MPD {mpd_product_id}")

        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania składu: {e}")

        return {}

    @staticmethod
    def _upload_product_images(mpd_product_id: int, matterhorn_product_id: int, producer_color_name: str = None) -> Dict:
        """Upload zdjęć produktu do bucketa i zapisz do MPD"""
        logger.info(f"🔄 Uploaduję zdjęcia dla produktu MPD {mpd_product_id}")

        try:
            from .defs_db import upload_image_to_bucket_and_get_url

            # Pobierz zdjęcia z matterhorn1
            with connections['matterhorn1'].cursor() as cursor:
                cursor.execute("""
                    SELECT image_url, "order"
                    FROM productimage 
                    WHERE product_id = %s 
                    AND image_url IS NOT NULL 
                    ORDER BY "order", id
                """, [matterhorn_product_id])
                images = cursor.fetchall()

            if not images:
                logger.info("ℹ️ Brak zdjęć do uploadu")
                return {"uploaded_images": 0}

            uploaded_count = 0
            uploaded_images = []

            with connections['MPD'].cursor() as mpd_cursor:
                for idx, (image_url, image_order) in enumerate(images, 1):
                    if image_url:
                        # Upload do bucketa
                        bucket_key = upload_image_to_bucket_and_get_url(
                            image_path=image_url,
                            product_id=mpd_product_id,
                            producer_color_name=producer_color_name,
                            image_number=idx
                        )

                        if bucket_key:
                            bucket_url = resolve_image_url(bucket_key)
                            # Zapisz do MPD
                            mpd_cursor.execute("""
                                INSERT INTO product_images (product_id, file_path)
                                VALUES (%s, %s)
                                ON CONFLICT (product_id, file_path) DO NOTHING
                            """, [mpd_product_id, bucket_key])

                            uploaded_count += 1
                            uploaded_images.append({
                                'original_url': image_url,
                                'uploaded_url': bucket_url,
                                'storage_key': bucket_key,
                                'order': image_order or idx
                            })
                            logger.info(
                                f"✅ Uploadowano zdjęcie {idx}: {bucket_url}")

            logger.info(
                f"✅ Uploadowano {uploaded_count} zdjęć do produktu MPD {mpd_product_id}")
            return {
                "uploaded_images": uploaded_count,
                "images": uploaded_images
            }

        except Exception as e:
            raise Exception(f"Failed to upload product images: {e}")

    @staticmethod
    def _remove_product_images(mpd_product_id: int, matterhorn_product_id: int = None, producer_color_name: str = None) -> Dict:
        """Usuń zdjęcia produktu z MPD (kompensacja)"""
        logger.info(f"🔄 Usuwam zdjęcia produktu MPD {mpd_product_id}")

        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    DELETE FROM product_images WHERE product_id = %s
                """, [mpd_product_id])

            logger.info(f"✅ Usunięto zdjęcia produktu MPD {mpd_product_id}")

        except Exception as e:
            logger.error(f"❌ Błąd podczas usuwania zdjęć: {e}")

        return {}

    @staticmethod
    def _create_mpd_product_variants(
            mpd_product_id: int,
            matterhorn_product_id: int,
            size_category: str,
            producer_code: str = None,
            main_color_id: int = None,
            producer_color_name: str = None
    ) -> Dict:
        """Utwórz warianty w MPD razem z produktem"""
        return saga_variants.create_mpd_variants(
            mpd_product_id, matterhorn_product_id, size_category,
            producer_code, main_color_id, producer_color_name
        )

    @staticmethod
    def _delete_mpd_product_variants(
            mpd_product_id: int,
            matterhorn_product_id: int = None,
            variant_ids: List[int] = None,
            **kwargs
    ) -> Dict:
        """Usuń warianty z MPD (kompensacja)"""
        return saga_variants.delete_mpd_variants(
            mpd_product_id, matterhorn_product_id, variant_ids, **kwargs
        )
