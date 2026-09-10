"""
`setup_stock_sync_task` - regresja na #270: rozszerzenie o --source nie może
zmienić domyślnego (matterhorn1) zachowania (nazwa/task_path/kwargs muszą
zostać identyczne, inaczej ponowne uruchomienie na prod stworzy DUPLIKAT
zamiast zaktualizować istniejący wpis).
"""
import json

import pytest
from django.core.management import call_command
from django_celery_beat.models import PeriodicTask

pytestmark = pytest.mark.django_db


def test_domyslne_zrodlo_to_matterhorn1_ze_starą_nazwą():
    call_command("setup_stock_sync_task")

    task = PeriodicTask.objects.get(name="Synchronizacja stanów MPD z Matterhorn1")
    assert task.task == "MPD.tasks.update_stock_from_matterhorn1"
    assert json.loads(task.kwargs) == {"time_window_minutes": 15}
    assert task.interval.every == 5


def test_source_tabu_tworzy_osobny_task_bez_kwargs():
    call_command("setup_stock_sync_task", "--source", "tabu")

    task = PeriodicTask.objects.get(name="Synchronizacja stanów MPD z Tabu")
    assert task.task == "MPD.tasks.update_stock_from_tabu"
    assert task.kwargs in ("", "{}", None)
    assert not PeriodicTask.objects.filter(name="Synchronizacja stanów MPD z Matterhorn1").exists()


def test_source_mada_tworzy_osobny_task():
    call_command("setup_stock_sync_task", "--source", "mada")

    task = PeriodicTask.objects.get(name="Synchronizacja stanów MPD z Mada")
    assert task.task == "MPD.tasks.update_stock_from_mada"


def test_trzy_zrodla_wspolistnieja_niezaleznie():
    call_command("setup_stock_sync_task", "--source", "matterhorn1")
    call_command("setup_stock_sync_task", "--source", "tabu")
    call_command("setup_stock_sync_task", "--source", "mada")

    names = set(
        PeriodicTask.objects.filter(task__startswith="MPD.tasks.").values_list("name", flat=True)
    )
    assert names == {
        "Synchronizacja stanów MPD z Matterhorn1",
        "Synchronizacja stanów MPD z Tabu",
        "Synchronizacja stanów MPD z Mada",
    }


def test_disable_tabu_nie_rusza_matterhorn1():
    call_command("setup_stock_sync_task")  # matterhorn1, enabled
    call_command("setup_stock_sync_task", "--source", "tabu", "--disable")

    mh = PeriodicTask.objects.get(name="Synchronizacja stanów MPD z Matterhorn1")
    tabu = PeriodicTask.objects.get(name="Synchronizacja stanów MPD z Tabu")
    assert mh.enabled is True
    assert tabu.enabled is False


def test_delete_tabu_nie_rusza_mada():
    call_command("setup_stock_sync_task", "--source", "tabu")
    call_command("setup_stock_sync_task", "--source", "mada")

    call_command("setup_stock_sync_task", "--source", "tabu", "--delete")

    assert not PeriodicTask.objects.filter(name="Synchronizacja stanów MPD z Tabu").exists()
    assert PeriodicTask.objects.filter(name="Synchronizacja stanów MPD z Mada").exists()
