"""
Saga Pattern dla operacji Mada ↔ MPD (dwie bazy).

Kroki: (1) utworzenie produktu i wariantów w MPD, (2) zapis mapowania w Mada.
W razie błędu kroku 2 kompensacja usuwa dane z MPD.

Sama logika wykonania kroków i persystencji do bazy (Saga/SagaStep) żyje we
wspólnej bazie core.saga — MadaSagaOrchestrator poniżej to tylko cienka
podklasa wskazująca konkretne modele i bazę danych mada.
"""
from core.saga import BaseSagaOrchestrator, SagaStatus, SagaStep, SagaResult
from core.db_routers import _get_mada_db
from .models import Saga, SagaStep as SagaStepModel


class MadaSagaOrchestrator(BaseSagaOrchestrator):
    """Orchestrator dla Saga Pattern w mada — zapisuje postęp do
    mada.models.Saga/SagaStep w bazie 'mada'."""

    saga_model = Saga
    step_model = SagaStepModel
    db_alias_getter = staticmethod(_get_mada_db)

    # step.execute_func (np. _saga_create_mpd_mada) zwraca mpd_product_id/variant_mapping,
    # których ten sam krok potrzebuje we własnym compensate_func (_saga_delete_mpd_mada) —
    # bez tego mergowania kompensacja nie dostałaby mpd_product_id do usunięcia.
    merge_result_into_own_step_data = True
