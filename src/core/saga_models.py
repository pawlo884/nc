from django.db import models


class SagaStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    COMPENSATING = "compensating", "Compensating"
    COMPENSATED = "compensated", "Compensated"


class AbstractSaga(models.Model):
    """Wspólne pola modelu Saga dla wszystkich hurtowni. Konkretna appka deklaruje
    własną podklasę z Meta (db_table/app_label/verbose_name)."""

    saga_id = models.CharField(max_length=100, unique=True, db_index=True)
    saga_type = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=SagaStatus.choices, default=SagaStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)

    total_steps = models.IntegerField(default=0)
    completed_steps = models.IntegerField(default=0)
    failed_step = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"Saga {self.saga_id} ({self.saga_type}) - {self.status}"


class AbstractSagaStep(models.Model):
    """Wspólne pola modelu SagaStep. FK do Saga oraz unique_together/ordering, które
    go używają, deklaruje konkretna appka (nie da się wskazać "siebie" z abstrakcyjnej
    bazy)."""

    step_name = models.CharField(max_length=100)
    step_order = models.IntegerField()

    status = models.CharField(
        max_length=20, choices=SagaStatus.choices, default=SagaStatus.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    compensated_at = models.DateTimeField(null=True, blank=True)

    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)

    compensation_attempted = models.BooleanField(default=False)
    compensation_successful = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.saga.saga_id} - Step {self.step_order}: {self.step_name} ({self.status})"
