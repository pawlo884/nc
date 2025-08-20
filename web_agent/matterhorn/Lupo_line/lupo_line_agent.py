#!/usr/bin/env python3
"""
Agent Lupo Line - główny plik uruchomieniowy
Robiący dokładnie to samo co products_navigator.py, ale z wyborem kategorii
"""

import os
import sys
import time
from products_navigator import ProductsNavigator, ProductEditor
from category_manager import category_manager
from skip_products_list import print_skip_list_status

# Sprawdź dostępność OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LupoLineAgent:
    """Główny agent do przetwarzania produktów Lupo Line"""

    def __init__(self, admin_url="http://localhost:8000/admin/",
                 username=None, password=None):
        """
        Inicjalizacja agenta Lupo Line
        
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
        print("🏊 === AGENT LUPO LINE ===\n")
        
        # Pokaż status listy pomijanych produktów
        print_skip_list_status()
        
        # Wybór kategorii
        selected_category = self._select_category()
        if not selected_category:
            print("❌ Nie wybrano kategorii. Kończę pracę.")
            return False
            
        # Uruchom przetwarzanie dla wybranej kategorii
        return self._process_category(selected_category)

    def _select_category(self):
        """Wybór kategorii produktów"""
        category_manager.show_category_menu()
        return category_manager.get_category_choice()

    def _process_category(self, category_config):
        """Przetwarzanie wybranej kategorii - dokładnie to samo co products_navigator.py"""
        print("🤖 === Agent do edycji produktów MPD (pełna automatyzacja) === 🤖")
        print("📋 Nazwa: AI optymalizacja + terminologia")
        print("📝 Długi opis: AI optymalizacja przez OpenAI")
        print("📄 Krótki opis: Pierwsze 1-2 zdania z długiego opisu")
        print("🏷️ Atrybuty MPD: Automatyczne wykrywanie z opisu")
        print("🔧 Pola MPD: Kategoria, kolory, seria, ścieżki, jednostka, materiał")
        print("💾 Zapisanie: Automatyczne kliknięcie 'Utwórz nowy produkt w MPD'")
        print("🔄 Pętla: Agent pracuje aż zabraknie produktów na stronie")
        print(f"🎯 Kategoria: {category_config['display_name']}")

        if not OPENAI_AVAILABLE:
            print("⚠️  WYMAGANE: pip install openai")

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  WYMAGANE: OPENAI_API_KEY w pliku .env.dev")
        else:
            print("✅ OpenAI API key znaleziony")

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
                max_products = 50  # Bezpiecznik - maksymalnie 50 produktów na sesję

                while processed_count < max_products:
                    print(f"\n{'='*60}")
                    print(f"🔄 PRODUKT {processed_count + 1} / maks. {max_products}")
                    print(f"{'='*60}")

                    # 1. Nawiguj i kliknij w pierwszy produkt
                    print("🚀 Szukam kolejnego produktu do przetworzenia...")
                    if nav.navigate_to_url_and_click_first_product(url):
                        print(f"✅ Dotarłem do produktu {processed_count + 1}!")

                        # 2. Edytuj wszystkie pola produktu
                        editor = ProductEditor(nav)
                        print("\n🤖 Analizuję i zmieniam nazwę, opis oraz krótki opis produktu...")

                        if editor.edit_all_fields(use_ai_optimization=True):
                            print("✅ Wszystkie pola produktu zostały zoptymalizowane!")

                            # 3. Automatyczne wykrywanie i ustawianie atrybutów MPD
                            print("\n🏷️ Wykrywam atrybuty MPD z opisu produktu...")
                            if editor.auto_detect_and_set_mpd_attributes():
                                print("✅ Atrybuty MPD zostały automatycznie wykryte i ustawione!")
                            else:
                                print("⚠️ Nie udało się wykryć lub ustawić atrybutów MPD")

                            # 4. Automatyczne ustawianie pól MPD
                            print("\n🔧 Ustawiam pola MPD (kategoria, kolory, seria, ścieżki, jednostka, materiał)...")
                            if editor.auto_setup_mpd_fields():
                                print("✅ Pola MPD zostały automatycznie ustawione!")
                            else:
                                print("⚠️ Nie udało się ustawić wszystkich pól MPD")

                            # 5. Zapisz produkt i wróć do listy (z filtrem is_mapped=0)
                            print("\n💾 Zapisuję produkt i wracam do listy...")
                            success, should_continue = editor.complete_mpd_process(url)

                            if success:
                                print(f"✅ Produkt {processed_count + 1} został pomyślnie przetworzony i zapisany!")
                                processed_count += 1
                            elif should_continue:
                                skipped_count += 1
                                print(f"⚠️ Produkt #{processed_count + skipped_count} pominięty (duplikat) - kontynuuję z następnym")
                                # Nie inkrementuj processed_count dla pominiętych produktów
                            else:
                                print(f"❌ Poważny błąd z produktem {processed_count + 1} - przerywam")
                                break

                        else:
                            print("❌ Nie udało się zmienić nazwy produktu")
                            break
                    else:
                        print("🏁 Brak więcej produktów do przetworzenia lub błąd nawigacji")
                        break

                    # Krótka pauza między produktami
                    print(f"\n⏳ Pauza 2 sekundy przed kolejnym produktem...")
                    time.sleep(2)

                print(f"\n{'='*60}")
                print(f"🎉 AGENT ZAKOŃCZYŁ PRACĘ!")
                print(f"📊 Przetworzone produkty: {processed_count}")
                print(f"⏭️ Pominięte produkty: {skipped_count}")
                print(f"🎯 Kategoria: {category_config['display_name']}")
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
    agent = LupoLineAgent(
        admin_url=admin_url,
        username=username,
        password=password
    )
    
    return agent.run()


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Agent Lupo Line zakończył pracę pomyślnie!")
        else:
            print("\n❌ Agent Lupo Line napotkał problemy.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Agent Lupo Line został zatrzymany przez użytkownika.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Nieoczekiwany błąd: {str(e)}")
        sys.exit(1)


