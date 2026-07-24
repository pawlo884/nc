"""
Saga Pattern — wspólna baza dla hurtowni (matterhorn1, tabu, ...).

Bezpieczne wykonywanie operacji rozciągniętych na dwie bazy danych (hurtownia + MPD):
każdy krok ma parę execute/compensate, a jeśli któryś krok zawiedzie, poprzednie kroki
są automatycznie cofane (kompensowane) w odwrotnej kolejności.

Postęp jest logowany do bazy (modele Saga/SagaStep konkretnej appki, patrz
core/saga_models.py) w sposób fail-open: błąd zapisu logu nigdy nie przerywa
właściwej sagi, tylko wyłącza dalsze logowanie dla tej instancji.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

from django.utils import timezone

logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    """Statusy Saga w trakcie wykonania (odpowiadają wartościom core.saga_models.SagaStatus)."""
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
    data: Dict[str, Any] = field(default_factory=dict)
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
    steps: List[SagaStep]
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None


class BaseSagaOrchestrator:
    """
    Orchestrator dla Saga Pattern.

    Subklasa ustawia `saga_model`/`step_model` (konkretne modele Saga/SagaStep danej
    appki) oraz `db_alias_getter` (callable zwracający alias bazy tej appki — patrz
    core/db_routers.py) i nie musi nadpisywać żadnej metody.
    """

    saga_model = None
    step_model = None
    db_alias_getter = None

    # tabu's execute_func results include kwargs (np. mpd_product_id) that its OWN
    # compensate_func needs but that aren't part of the step's original `data` — włączenie
    # tej flagi merguje wynik kroku z powrotem do jego własnych danych, żeby
    # `compensate_func(**step.data)` je dostał. matterhorn1's compensate funkcje nie są
    # na to zaprojektowane (część nie przyjmuje **kwargs), więc zostaje False tam.
    merge_result_into_own_step_data = False

    def __init__(self, saga_id: str = None, saga_type: str = "generic", enable_logging: bool = True):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.saga_type = saga_type
        self.enable_logging = enable_logging
        self.steps: List[SagaStep] = []
        self.status = SagaStatus.PENDING
        self.created_at = timezone.now()
        self.error = None
        self.saga_log = None

        if self.enable_logging:
            self._create_saga_log()

    def _db(self):
        return self.db_alias_getter()

    def add_step(self, name: str, execute_func: Callable, compensate_func: Callable, data: Dict[str, Any] = None):
        """Dodaj krok do Saga"""
        step = SagaStep(
            name=name,
            execute_func=execute_func,
            compensate_func=compensate_func,
            data=data or {}
        )
        self.steps.append(step)
        logger.info("Saga %s: dodano krok '%s'", self.saga_id, name)

        if self.enable_logging and self.saga_log:
            self._create_step_log(step)

        return self

    def _create_saga_log(self):
        """Utwórz log Saga w bazie danych"""
        try:
            self.saga_log = self.saga_model.objects.using(self._db()).create(
                saga_id=self.saga_id,
                saga_type=self.saga_type,
                status=SagaStatus.PENDING.value,
                input_data={}
            )
            logger.info("Saga %s: utworzono log w bazie danych", self.saga_id)
        except Exception as e:
            logger.warning("Saga %s: nie udało się utworzyć logu: %s", self.saga_id, e)
            self.enable_logging = False

    def _create_step_log(self, step: SagaStep):
        """Utwórz log kroku w bazie danych"""
        try:
            self.step_model.objects.using(self._db()).create(
                saga=self.saga_log,
                step_name=step.name,
                step_order=len(self.steps),
                status=SagaStatus.PENDING.value,
                input_data=step.data or {}
            )
        except Exception as e:
            logger.warning("Saga %s: nie udało się utworzyć logu kroku '%s': %s", self.saga_id, step.name, e)

    def _update_saga_log(self, status: SagaStatus, error: str = None, *,
                          total_steps: int = None, completed_steps: int = None,
                          failed_step: str = None):
        """Aktualizuj log Saga w bazie danych"""
        if not self.enable_logging or not self.saga_log:
            return

        try:
            self.saga_log.status = status.value
            if error:
                self.saga_log.error_message = error
            if total_steps is not None:
                self.saga_log.total_steps = total_steps
            if completed_steps is not None:
                self.saga_log.completed_steps = completed_steps
            if failed_step is not None:
                self.saga_log.failed_step = failed_step
            if status == SagaStatus.RUNNING:
                self.saga_log.started_at = timezone.now()
            elif status in (SagaStatus.COMPLETED, SagaStatus.COMPENSATED):
                self.saga_log.completed_at = timezone.now()
            self.saga_log.save()
        except Exception as e:
            logger.warning("Saga %s: nie udało się zaktualizować logu: %s", self.saga_id, e)

    def _update_step_log(self, step: SagaStep, status: SagaStatus, error: str = None, output_data: Dict = None):
        """Aktualizuj log kroku w bazie danych"""
        if not self.enable_logging or not self.saga_log:
            return

        try:
            step_log = self.step_model.objects.using(self._db()).get(
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
            logger.warning("Saga %s: nie udało się zaktualizować logu kroku '%s': %s", self.saga_id, step.name, e)

    def execute(self) -> SagaResult:
        """
        Wykonaj wszystkie kroki Saga.

        Jeśli któryś krok się nie powiedzie, wykonaj kompensację dla wszystkich
        poprzednich kroków w odwrotnej kolejności.
        """
        logger.info("Saga %s: rozpoczynam wykonanie %d kroków", self.saga_id, len(self.steps))
        self.status = SagaStatus.RUNNING
        self._update_saga_log(self.status, total_steps=len(self.steps))

        try:
            for i, step in enumerate(self.steps):
                result = self._execute_step(step)
                step.result = result

                if result and i < len(self.steps) - 1:
                    for next_step in self.steps[i + 1:]:
                        for key, value in result.items():
                            if key in next_step.data and next_step.data[key] is None:
                                next_step.data[key] = value
                                logger.info(
                                    "Saga %s: przekazuję %s=%s do kroku '%s'",
                                    self.saga_id, key, value, next_step.name)

            self.status = SagaStatus.COMPLETED
            self._update_saga_log(self.status, completed_steps=len(self.steps))
            logger.info("Saga %s: wszystkie kroki wykonane pomyślnie", self.saga_id)

        except Exception as e:
            logger.error("Saga %s: błąd podczas wykonywania: %s", self.saga_id, e)
            self.error = str(e)
            completed_count = sum(1 for s in self.steps if s.status == SagaStatus.COMPLETED)
            failed_step_name = next((s.name for s in self.steps if s.status == SagaStatus.FAILED), None)
            self._update_saga_log(
                self.status, str(e),
                completed_steps=completed_count, failed_step=failed_step_name,
            )
            self._compensate()

        return self._create_result()

    def _execute_step(self, step: SagaStep):
        """Wykonaj pojedynczy krok"""
        logger.info("Saga %s: wykonuję krok '%s'", self.saga_id, step.name)
        step.status = SagaStatus.RUNNING
        self._update_step_log(step, step.status)

        try:
            result = step.execute_func(**step.data)
            step.status = SagaStatus.COMPLETED
            step.executed_at = timezone.now()
            self._update_step_log(step, step.status, output_data=result)
            if self.merge_result_into_own_step_data and result:
                step.data.update(result)

            logger.info("Saga %s: krok '%s' wykonany pomyślnie", self.saga_id, step.name)
            return result

        except Exception as e:
            step.status = SagaStatus.FAILED
            step.error = str(e)
            self._update_step_log(step, step.status, str(e))
            logger.error("Saga %s: błąd w kroku '%s': %s", self.saga_id, step.name, e)
            raise

    def _compensate(self):
        """Wykonaj kompensację dla wszystkich wykonanych kroków"""
        logger.info("Saga %s: rozpoczynam kompensację", self.saga_id)
        self.status = SagaStatus.COMPENSATING
        self._update_saga_log(self.status)

        executed_steps = [step for step in self.steps if step.status == SagaStatus.COMPLETED]

        for step in reversed(executed_steps):
            try:
                logger.info("Saga %s: kompensuję krok '%s'", self.saga_id, step.name)
                step.compensate_func(**step.data)
                step.compensated_at = timezone.now()
                self._update_step_log(step, SagaStatus.COMPENSATED)
                logger.info("Saga %s: krok '%s' skompensowany", self.saga_id, step.name)

            except Exception as e:
                logger.error("Saga %s: błąd kompensacji kroku '%s': %s", self.saga_id, step.name, e)
                self._update_step_log(step, SagaStatus.FAILED, str(e))
                # Kontynuuj kompensację innych kroków

        self.status = SagaStatus.COMPENSATED
        self._update_saga_log(self.status)
        logger.info("Saga %s: kompensacja zakończona", self.saga_id)

    def _create_result(self) -> SagaResult:
        """Utwórz wynik Saga"""
        return SagaResult(
            saga_id=self.saga_id,
            status=self.status,
            steps=self.steps.copy(),
            error=self.error,
            created_at=self.created_at,
            completed_at=datetime.now() if self.status in (
                SagaStatus.COMPLETED, SagaStatus.COMPENSATED) else None
        )
