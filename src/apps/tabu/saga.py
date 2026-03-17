"""
Saga Pattern dla operacji Tabu ↔ MPD (dwie bazy).

Kroki: (1) utworzenie produktu i wariantów w MPD, (2) zapis mapowania w Tabu.
W razie błędu kroku 2 kompensacja usuwa dane z MPD.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


@dataclass
class SagaStep:
    name: str
    execute_func: Callable
    compensate_func: Callable
    data: Dict[str, Any]
    status: SagaStatus = SagaStatus.PENDING
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class SagaResult:
    saga_id: str
    status: SagaStatus
    steps: List[SagaStep]
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


class TabuSagaOrchestrator:
    """Orchestrator Saga dla Tabu → MPD (bez logowania do bazy)."""

    def __init__(self, saga_id: Optional[str] = None):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.steps: List[SagaStep] = []
        self.status = SagaStatus.PENDING
        self.error: Optional[str] = None

    def add_step(
        self,
        name: str,
        execute_func: Callable,
        compensate_func: Callable,
        data: Optional[Dict[str, Any]] = None,
    ) -> "TabuSagaOrchestrator":
        self.steps.append(
            SagaStep(
                name=name,
                execute_func=execute_func,
                compensate_func=compensate_func,
                data=data or {},
            )
        )
        return self

    def execute(self) -> SagaResult:
        self.status = SagaStatus.RUNNING
        try:
            for i, step in enumerate(self.steps):
                result = self._execute_step(step)
                step.result = result
                # Żeby kompensacja miała dostęp do wyników (np. mpd_product_id)
                if result:
                    step.data.update(result)
                if result and i < len(self.steps) - 1:
                    for next_step in self.steps[i + 1:]:
                        for k, v in result.items():
                            if k in next_step.data and next_step.data[k] is None:
                                next_step.data[k] = v
            self.status = SagaStatus.COMPLETED
        except Exception as e:
            self.error = str(e)
            logger.exception("Saga %s błąd: %s", self.saga_id, e)
            self._compensate()
        return self._create_result()

    def _execute_step(self, step: SagaStep) -> Dict[str, Any]:
        logger.info("Saga %s: krok '%s'", self.saga_id, step.name)
        step.status = SagaStatus.RUNNING
        try:
            result = step.execute_func(**step.data)
            step.status = SagaStatus.COMPLETED
            return result or {}
        except Exception as e:
            step.status = SagaStatus.FAILED
            step.error = str(e)
            raise

    def _compensate(self) -> None:
        self.status = SagaStatus.COMPENSATING
        executed = [s for s in self.steps if s.status == SagaStatus.COMPLETED]
        for step in reversed(executed):
            try:
                logger.info("Saga %s: kompensacja '%s'", self.saga_id, step.name)
                step.compensate_func(**step.data)
            except Exception as e:
                logger.exception("Saga %s: błąd kompensacji '%s': %s", self.saga_id, step.name, e)
        self.status = SagaStatus.COMPENSATED

    def _create_result(self) -> SagaResult:
        return SagaResult(
            saga_id=self.saga_id,
            status=self.status,
            steps=list(self.steps),
            error=self.error,
            completed_at=datetime.utcnow() if self.status in (SagaStatus.COMPLETED, SagaStatus.COMPENSATED) else None,
        )
