"""
Agent Marko - główny plik uruchomieniowy
Inteligentny agent do przetwarzania produktów marki Marko z wykorzystaniem embeddings
"""

import os
import sys
import time
from products_navigator import ProductsNavigator, ProductEditor
from marko_category_manager import marko_category_manager
from skip_products_list import print_skip_list_status

# Sprawdź dostępność OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class MarkoAgent:
    """Główny agent do przetwarzania produktów marki Marko"""

    def __init__(self, admin_url="http://localhost:8000/admin/",
                 username=None, password=None):
        """
        Inicjalizacja agenta Marko

        Args:
            admin_url (str): URL panelu admina
            username (str): Nazwa użytkownika
            password (str): Hasło
        """
        self.admin_url = admin_url
        self.username = username
        self.password = password

    def run(self):
        """Główna pętla agenta"""
        print("🏷️ === AGENT MARKO ===\n")

        # Pokaż informacje o marce
        marko_category_manager.show_brand_info()

        # Pokaż status listy pomijanych produktów
        print_skip_list_status()

        # Pokaż rekomendacje dotyczące uczenia się
        recommendations = marko_category_manager.get_learning_recommendations()
        if recommendations:
            print("\n💡 REKOMENDACJE:")
            for rec in recommendations:
                print(f"   {rec}")
            print()

        # Wybór kategorii
        selected_category = self._select_category()
        if not selected_category:
            print("❌ Nie wybrano kategorii. Kończę pracę.")
            return False

        # Uruchom przetwarzanie dla wybranej kategorii
        return self._process_category(selected_category)

    def _select_category(self):
        """Wybór kategorii produktów"""
        marko_category_manager.show_category_menu()
        return marko_category_manager.get_category_choice()

    def _process_category(self, category_config):
        """Przetwarzanie wybranej kategorii z wykorzystaniem embeddings"""
        print("🤖 === Agent do edycji produktów Marko (AI + Embeddings) === 🤖")
        print("📋 Nazwa: AI optymalizacja + terminologia + embeddings")
        print("📝 Długi opis: AI optymalizacja przez OpenAI + uczenie się")
        print("📄 Krótki opis: Pierwsze 1-2 zdania z długiego opisu")
        print("🏷️ Atrybuty MPD: Automatyczne wykrywanie z embeddings")
        print("🔧 Pola MPD: Kategoria, kolory, seria, ścieżki, jednostka, materiał")
        print("💾 Zapisanie: Automatyczne kliknięcie 'Utwórz nowy produkt w MPD'")
        print("🔄 Pętla: Agent pracuje aż zabraknie produktów na stronie")
        print("🧠 Uczenie: System uczy się z każdego przetworzonego produktu")
        print(f"🎯 Kategoria: {category_config['display_name']}")

        if not OPENAI_AVAILABLE:
            print("⚠️  WYMAGANE: pip install openai")

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  WYMAGANE: OPENAI_API_KEY w pliku .env.dev")
        else:
            print("✅ OpenAI API key znaleziony")

        # Sprawdź dostępność embeddings
        try:
            from marko_knowledge_base import EMBEDDINGS_AVAILABLE
            if EMBEDDINGS_AVAILABLE:
                print("✅ Embeddings są dostępne - system będzie się uczył")
            else:
                print("⚠️ Embeddings niedostępne - tylko reguły bazowe")
        except ImportError:
            print("⚠️ Embeddings niedostępne - tylko reguły bazowe")

        print()

        try:
            with ProductsNavigator(
                admin_url=self.admin_url,
                username=self.username,
                password=self.password
            ) as nav:
                url = category_config["url"]

                processed_count = 0
                skipped_count = 0  # Liczba produktów pominiętych (duplikaty)
                learned_count = 0  # Liczba produktów użytych do nauki
                max_products = 50  # Bezpiecznik - maksymalnie 50 produktów na sesję

                while processed_count < max_products:
                    print(f"\n{'='*60}")
                    print(
                        f"🔄 PRODUKT {processed_count + 1} / maks. {max_products}")
                    print(f"{'='*60}")

                    # 1. Nawiguj i kliknij w pierwszy produkt
                    print("🚀 Szukam kolejnego produktu do przetworzenia...")
                    if nav.navigate_to_url_and_click_first_product(url):
                        print(f"✅ Dotarłem do produktu {processed_count + 1}!")

                        # 2. Edytuj wszystkie pola produktu
                        editor = ProductEditor(nav)
                        print(
                            "\n🤖 Analizuję i zmieniam nazwę, opis oraz krótki opis produktu...")

                        if editor.edit_all_fields(use_ai_optimization=True):
                            print(
                                "✅ Wszystkie pola produktu zostały zoptymalizowane!")

                            # 3. Automatyczne wykrywanie i ustawianie atrybutów MPD z embeddings
                            print(
                                "\n🧠 Wykrywam atrybuty MPD z embeddings i bazy wiedzy...")
                            if editor.auto_detect_and_set_mpd_attributes():
                                print(
                                    "✅ Atrybuty MPD zostały automatycznie wykryte i ustawione!")
                            else:
                                print(
                                    "⚠️ Nie udało się wykryć lub ustawić atrybutów MPD")

                            # 4. Automatyczne ustawianie pól MPD
                            print(
                                "\n🔧 Ustawiam pola MPD (kategoria, kolory, seria, ścieżki, jednostka, materiał)...")
                            if editor.auto_setup_mpd_fields():
                                print("✅ Pola MPD zostały automatycznie ustawione!")
                            else:
                                print("⚠️ Nie udało się ustawić wszystkich pól MPD")

                            # 5. Zapisz produkt i wróć do listy (z filtrem is_mapped=0)
                            print("\n💾 Zapisuję produkt i wracam do listy...")
                            success, should_continue = editor.complete_mpd_process(
                                url)

                            if success:
                                print(
                                    f"✅ Produkt {processed_count + 1} został pomyślnie przetworzony i zapisany!")
                                processed_count += 1

                                # 6. Ucz się z przetworzonego produktu (dodaj do embeddings)
                                try:
                                    # Pobierz dane produktu do nauki
                                    title = editor.get_current_title()
                                    description = editor.get_current_description()
                                    category = category_config.get(
                                        "category_name", "nieznana")

                                    # Użyj bazy wiedzy do przewidzenia atrybutów
                                    from marko_knowledge_base import marko_knowledge
                                    predictions = marko_knowledge.get_smart_predictions(
                                        title, description)

                                    # Dodaj do embeddings
                                    marko_knowledge.learn_from_product(
                                        product_id=processed_count,  # Tymczasowy ID
                                        title=title,
                                        description=description,
                                        category=category,
                                        attributes=predictions.get(
                                            "attributes", []),
                                        model_name=predictions.get(
                                            "model_name")
                                    )
                                    learned_count += 1
                                    print(
                                        f"🧠 Nauczono się z produktu {processed_count} (pewność: {predictions.get('confidence', 0):.2f})")

                                except Exception as e:
                                    print(f"⚠️ Błąd podczas uczenia się: {e}")

                            elif should_continue:
                                skipped_count += 1
                                print(
                                    f"⚠️ Produkt #{processed_count + skipped_count} pominięty (duplikat) - kontynuuję z następnym")
                                # Nie inkrementuj processed_count dla pominiętych produktów
                            else:
                                print(
                                    f"❌ Poważny błąd z produktem {processed_count + 1} - przerywam")
                                break

                        else:
                            print("❌ Nie udało się zmienić nazwy produktu")
                            break
                    else:
                        print(
                            "🏁 Brak więcej produktów do przetworzenia lub błąd nawigacji")
                        break

                    # Krótka pauza między produktami
                    print(f"\n⏳ Pauza 2 sekundy przed kolejnym produktem...")
                    time.sleep(2)

                print(f"\n{'='*60}")
                print(f"🎉 AGENT MARKO ZAKOŃCZYŁ PRACĘ!")
                print(f"📊 Przetworzone produkty: {processed_count}")
                print(f"⏭️ Pominięte produkty: {skipped_count}")
                print(f"🧠 Nauczone produkty: {learned_count}")
                print(f"🎯 Kategoria: {category_config['display_name']}")
                if (processed_count + skipped_count) > 0:
                    success_rate = (processed_count /
                                    (processed_count + skipped_count)) * 100
                    print(f"📈 Skuteczność: {success_rate:.1f}%")
                else:
                    print("📈 Skuteczność: N/A")

                # Pokaż statystyki embeddings
                if EMBEDDINGS_AVAILABLE:
                    stats = marko_knowledge.get_learning_statistics()
                    if stats.get("embeddings_available"):
                        print(
                            f"🧠 Produktów w bazie wiedzy: {stats.get('total_products', 0)}")

                print(f"{'='*60}")

                return True

        except Exception as e:
            print(f"❌ Błąd podczas przetwarzania: {str(e)}")
            return False


def main():
    """Główna funkcja uruchomieniowa"""
    # Pobierz dane logowania z zmiennych środowiskowych
    username = os.getenv('DJANGO_ADMIN_USERNAME')
    password = os.getenv('DJANGO_ADMIN_PASSWORD')
    admin_url = os.getenv('DJANGO_ADMIN_URL', 'http://localhost:8000/admin/')

    if not username or not password:
        print("❌ Błąd: Brak danych logowania")
        print("Ustaw zmienne środowiskowe:")
        print("- DJANGO_ADMIN_USERNAME")
        print("- DJANGO_ADMIN_PASSWORD")
        print("- DJANGO_ADMIN_URL (opcjonalnie)")
        return False

    # Utwórz i uruchom agenta
    agent = MarkoAgent(
        admin_url=admin_url,
        username=username,
        password=password
    )

    return agent.run()


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Agent Marko zakończył pracę pomyślnie!")
        else:
            print("\n❌ Agent Marko napotkał problemy.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Agent Marko został zatrzymany przez użytkownika.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Nieoczekiwany błąd: {str(e)}")
        sys.exit(1)
