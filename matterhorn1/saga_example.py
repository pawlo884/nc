"""
Przykład użycia Saga Pattern w matterhorn1

Ten plik pokazuje jak używać Saga Pattern do bezpiecznych operacji
między bazami danych.
"""

from matterhorn1.saga import SagaService, SagaOrchestrator
import logging

logger = logging.getLogger(__name__)


def example_create_product_with_mapping():
    """
    Przykład tworzenia produktu z mapping między matterhorn1 i MPD
    """
    logger.info("🚀 Przykład: Tworzenie produktu z mapping")

    # Dane produktu dla matterhorn1
    matterhorn_data = {
        'product_id': 12345,  # ID istniejącego produktu w matterhorn1
        'mpd_product_id': None  # Będzie wypełnione przez Saga
    }

    # Dane produktu dla MPD
    mpd_data = {
        'name': 'Test Product',
        'description': 'Test Description',
        'brand_id': 1,
        'category_id': 1,
        'attributes': [1, 2, 3]  # ID atrybutów do dodania
    }

    try:
        # Użyj Saga Pattern
        result = SagaService.create_product_with_mapping(
            matterhorn_data, mpd_data)

        if result.status.value == 'completed':
            logger.info("✅ Saga zakończona pomyślnie")
            logger.info(f"📊 Saga ID: {result.saga_id}")
            logger.info(f"📊 Wykonane kroki: {len(result.steps)}")

            # Sprawdź wyniki kroków
            for step in result.steps:
                logger.info(f"  - {step.name}: {step.status.value}")
                if step.status.value == 'completed' and hasattr(step, 'executed_at'):
                    logger.info(f"    Wykonano: {step.executed_at}")
        else:
            logger.error("❌ Saga nie powiodła się")
            logger.error(f"❌ Błąd: {result.error}")

            # Sprawdź które kroki się nie powiodły
            for step in result.steps:
                if step.status.value == 'failed':
                    logger.error(f"  ❌ {step.name}: {step.error}")
                elif step.status.value == 'compensated':
                    logger.info(f"  🔄 {step.name}: skompensowany")

    except Exception as e:
        logger.error(f"❌ Błąd podczas wykonywania Saga: {e}")


def example_custom_saga():
    """
    Przykład tworzenia własnej Saga z niestandardowymi krokami
    """
    logger.info("🚀 Przykład: Własna Saga")

    # Utwórz własną Saga
    saga = SagaOrchestrator(saga_type="custom_operation")

    # Definicje funkcji kroków
    def step1_create_user(user_data):
        """Krok 1: Utwórz użytkownika"""
        logger.info(f"🔄 Tworzę użytkownika: {user_data['name']}")
        # Symulacja operacji
        user_id = 12345
        logger.info(f"✅ Utworzono użytkownika z ID: {user_id}")
        return {'user_id': user_id}

    def step1_compensate_user(user_data, user_id=None):
        """Kompensacja kroku 1: Usuń użytkownika"""
        if user_id:
            logger.info(f"🔄 Usuwam użytkownika: {user_id}")
            # Symulacja usunięcia
            logger.info(f"✅ Usunięto użytkownika: {user_id}")

    def step2_create_profile(user_data, user_id=None):
        """Krok 2: Utwórz profil użytkownika"""
        logger.info(f"🔄 Tworzę profil dla użytkownika: {user_id}")
        # Symulacja operacji
        profile_id = 67890
        logger.info(f"✅ Utworzono profil z ID: {profile_id}")
        return {'profile_id': profile_id}

    def step2_compensate_profile(user_data, user_id=None):
        """Kompensacja kroku 2: Usuń profil"""
        logger.info(f"🔄 Usuwam profil użytkownika: {user_id}")
        # Symulacja usunięcia
        logger.info(f"✅ Usunięto profil użytkownika: {user_id}")

    # Dodaj kroki do Saga
    saga.add_step(
        name="create_user",
        execute_func=step1_create_user,
        compensate_func=step1_compensate_user,
        data={'name': 'Test User', 'email': 'test@example.com'}
    )

    saga.add_step(
        name="create_profile",
        execute_func=step2_create_profile,
        compensate_func=step2_compensate_profile,
        data={'user_id': None}  # Będzie wypełnione przez poprzedni krok
    )

    # Wykonaj Saga
    try:
        result = saga.execute()

        if result.status.value == 'completed':
            logger.info("✅ Własna Saga zakończona pomyślnie")
        else:
            logger.error("❌ Własna Saga nie powiodła się")

    except Exception as e:
        logger.error(f"❌ Błąd podczas wykonywania własnej Saga: {e}")


def example_variants_creation():
    """
    Przykład tworzenia wariantów z mapping
    """
    logger.info("🚀 Przykład: Tworzenie wariantów")

    # Dane wariantów
    variants_data = [
        {
            'variant_id': 'var_001',
            'variant_uid': 'uid_001',
            'color_id': 1,
            'size_id': 1,
            'producer_code': 'PC001',
            'iai_product_id': 1001
        },
        {
            'variant_id': 'var_002',
            'variant_uid': 'uid_002',
            'color_id': 1,
            'size_id': 2,
            'producer_code': 'PC002',
            'iai_product_id': 1002
        }
    ]

    try:
        # Użyj Saga Pattern dla wariantów
        result = SagaService.create_variants_with_mapping(
            product_id=12345,
            mpd_product_id=67890,
            variants_data=variants_data
        )

        if result.status.value == 'completed':
            logger.info("✅ Warianty utworzone pomyślnie")
        else:
            logger.error("❌ Tworzenie wariantów nie powiodło się")

    except Exception as e:
        logger.error(f"❌ Błąd podczas tworzenia wariantów: {e}")


if __name__ == "__main__":
    # Uruchom przykłady
    print("=== PRZYKŁADY SAGA PATTERN ===\n")

    print("1. Tworzenie produktu z mapping:")
    example_create_product_with_mapping()

    print("\n2. Własna Saga:")
    example_custom_saga()

    print("\n3. Tworzenie wariantów:")
    example_variants_creation()

    print("\n=== KONIEC PRZYKŁADÓW ===")

