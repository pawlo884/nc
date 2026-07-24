"""
Testy SagaOrchestrator (persystencja Saga/SagaStep) w matterhorn1: sukces oraz
kompensacja przy błędzie kroku. Dodane przy okazji przeniesienia orchestratora
na wspólną bazę core.saga.BaseSagaOrchestrator — matterhorn1 nie miało wcześniej
dedykowanego testu na tę logikę (tylko na saga_variants.py).
"""
from django.conf import settings
from django.test import TestCase

from matterhorn1.models import Saga, SagaStep
from matterhorn1.saga import SagaOrchestrator


def _mh_db():
    return 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'


class SagaOrchestratorPersistenceTest(TestCase):
    """Testy zapisu postępu Saga do bazy: sukces oraz kompensacja przy błędzie kroku."""

    databases = '__all__'

    def test_saga_success_persists_completed_status(self):
        mh_db = _mh_db()
        calls = []

        def execute_step_one(**kwargs):
            calls.append('execute_one')
            return {'value': 42}

        def compensate_step_one(**kwargs):
            calls.append('compensate_one')

        def execute_step_two(value=None, **kwargs):
            calls.append(('execute_two', value))
            return {}

        def compensate_step_two(**kwargs):
            calls.append('compensate_two')

        saga = SagaOrchestrator(saga_type='test_success')
        saga.add_step('step_one', execute_step_one, compensate_step_one, data={})
        saga.add_step('step_two', execute_step_two, compensate_step_two, data={'value': None})
        result = saga.execute()

        self.assertEqual(result.status.value, 'completed')
        self.assertEqual(calls, ['execute_one', ('execute_two', 42)])

        saga_row = Saga.objects.using(mh_db).get(saga_id=saga.saga_id)
        self.assertEqual(saga_row.status, 'completed')
        self.assertEqual(saga_row.saga_type, 'test_success')
        self.assertEqual(saga_row.total_steps, 2)
        self.assertEqual(saga_row.completed_steps, 2)
        self.assertIsNotNone(saga_row.started_at)
        self.assertIsNotNone(saga_row.completed_at)

        steps = list(SagaStep.objects.using(mh_db).filter(saga=saga_row).order_by('step_order'))
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].step_name, 'step_one')
        self.assertEqual(steps[0].status, 'completed')
        self.assertEqual(steps[0].output_data, {'value': 42})
        self.assertEqual(steps[1].step_name, 'step_two')
        self.assertEqual(steps[1].status, 'completed')

    def test_saga_compensation_when_step_fails(self):
        mh_db = _mh_db()

        def execute_step_one(**kwargs):
            return {'created_id': 7}

        def compensate_step_one(**kwargs):
            pass

        def execute_step_two(**kwargs):
            raise RuntimeError('Symulowany błąd kroku 2')

        def compensate_step_two(**kwargs):
            pass

        saga = SagaOrchestrator(saga_type='test_compensation')
        saga.add_step('step_one', execute_step_one, compensate_step_one, data={})
        saga.add_step('step_two', execute_step_two, compensate_step_two, data={})
        result = saga.execute()

        self.assertEqual(result.status.value, 'compensated')
        self.assertIn('Symulowany błąd kroku 2', result.error)

        saga_row = Saga.objects.using(mh_db).get(saga_id=saga.saga_id)
        self.assertEqual(saga_row.status, 'compensated')
        self.assertEqual(saga_row.completed_steps, 1)
        self.assertEqual(saga_row.failed_step, 'step_two')

        steps = {s.step_name: s for s in SagaStep.objects.using(mh_db).filter(saga=saga_row)}
        self.assertEqual(steps['step_one'].status, 'compensated')
        self.assertTrue(steps['step_one'].compensation_attempted)
        self.assertTrue(steps['step_one'].compensation_successful)
        self.assertEqual(steps['step_two'].status, 'failed')
