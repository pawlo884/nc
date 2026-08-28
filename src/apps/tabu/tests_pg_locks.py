"""
Testy dla core.pg_locks.advisory_lock (PostgreSQL advisory locks).

Umieszczone w aplikacji `tabu`, bo to jej taski (razem z `mada`) są głównym
konsumentem advisory locków; `core` nie jest aplikacją Django z własnym suite.
"""
from django.test import TransactionTestCase

from core.pg_locks import advisory_lock


class AdvisoryLockTests(TransactionTestCase):
    databases = {'default'}

    def test_acquire_and_reacquire_after_release(self):
        name = 'test:acquire_release'
        with advisory_lock(name) as acquired:
            self.assertTrue(acquired)
        # po wyjściu z bloku lock jest zwolniony -> można wziąć ponownie
        with advisory_lock(name) as again:
            self.assertTrue(again)

    def test_second_acquire_is_blocked(self):
        name = 'test:mutual_exclusion'
        with advisory_lock(name) as first:
            self.assertTrue(first)
            with advisory_lock(name) as second:
                self.assertFalse(second)
        with advisory_lock(name) as third:
            self.assertTrue(third)

    def test_different_names_do_not_collide(self):
        with advisory_lock('test:name_a') as a, advisory_lock('test:name_b') as b:
            self.assertTrue(a)
            self.assertTrue(b)

    def test_lock_released_after_exception(self):
        name = 'test:exception_release'
        with self.assertRaises(RuntimeError):
            with advisory_lock(name) as acquired:
                self.assertTrue(acquired)
                raise RuntimeError('boom')
        with advisory_lock(name) as again:
            self.assertTrue(again)
