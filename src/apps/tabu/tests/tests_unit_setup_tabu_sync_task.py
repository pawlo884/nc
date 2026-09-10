"""
`setup_tabu_sync_task` — regresja na #267/#269: PeriodicTask dla
`sync_tabu_products_update` nie może mieć jawnego `queue`, bo to wygrywa z
`CELERY_TASK_ROUTES` (który kieruje ten task na `heavy`) i wysyła długi
(do 3h) task na `celery-fast`.
"""
from __future__ import annotations

import pytest
from django.core.management import call_command
from django_celery_beat.models import PeriodicTask

pytestmark = pytest.mark.django_db

TASK_NAME = "Synchronizacja produktów Tabu"


def test_nowy_task_ma_puste_queue():
    call_command("setup_tabu_sync_task")

    task = PeriodicTask.objects.get(name=TASK_NAME)
    assert task.queue in (None, "")
    assert task.task == "tabu.tasks.sync_tabu_products_update"


def test_istniejacy_task_ze_starym_queue_zostaje_wyczyszczony():
    """Regresja na sam bug: stary wpis miał queue='default' na sztywno -
    ponowne uruchomienie setup command musi to wyczyścić, nie tylko
    ustawiać gdy puste."""
    from django_celery_beat.models import IntervalSchedule

    interval, _ = IntervalSchedule.objects.get_or_create(every=60, period="minutes")
    PeriodicTask.objects.create(
        name=TASK_NAME,
        task="tabu.tasks.sync_tabu_products_update",
        interval=interval,
        queue="default",
    )

    call_command("setup_tabu_sync_task")

    task = PeriodicTask.objects.get(name=TASK_NAME)
    assert task.queue in (None, "")
