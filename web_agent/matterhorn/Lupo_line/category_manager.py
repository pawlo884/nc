#!/usr/bin/env python3
"""
Menedżer kategorii produktów Lupo Line
Pozwala na wybór i zarządzanie różnymi kategoriami produktów
"""

from lupo_line_knowledge_base import lupo_knowledge


class CategoryManager:
    """Menedżer kategorii produktów"""

    def __init__(self):
        self.available_categories = {
            "1": {
                "name": "stroj_dwuczesciowy",
                "display_name": "Stroje Dwuczęściowe",
                "description": "Biustonosze, bralety, figi, kopy - stroje dwuczęściowe",
                "url": "http://localhost:8000/admin/matterhorn/products/?active=true&brand=Lupo+Line&category_name=Kostiumy+Dwuczęściowe&is_mapped__exact=0"
            },
            "2": {
                "name": "stroj_jednoczesciowy", 
                "display_name": "Stroje Jednoczęściowe",
                "description": "Stroje jednoczęściowe, kostiumy one-piece",
                "url": "http://localhost:8000/admin/matterhorn/products/?active=true&brand=Lupo+Line&category_name=Jednoczęściowe&is_mapped__exact=0"
            }
        }

    def show_category_menu(self):
        """Wyświetla menu wyboru kategorii"""
        print("\n🎯 === WYBÓR KATEGORII PRODUKTÓW LUPO LINE ===\n")
        
        for key, category in self.available_categories.items():
            print(f"{key}. {category['display_name']}")
            print(f"   📝 {category['description']}")
            print()

    def get_category_choice(self):
        """Pobiera wybór kategorii od użytkownika"""
        while True:
            try:
                choice = input("Wybierz kategorię (1-2): ").strip()
                
                if choice in self.available_categories:
                    selected_category = self.available_categories[choice]
                    print(f"\n✅ Wybrano: {selected_category['display_name']}")
                    print(f"📝 {selected_category['description']}")
                    return selected_category
                else:
                    print("❌ Nieprawidłowy wybór. Wybierz 1-2.")
                    
            except KeyboardInterrupt:
                print("\n\n❌ Anulowano wybór kategorii.")
                return None
            except Exception as e:
                print(f"❌ Błąd: {str(e)}")

    def get_category_by_name(self, category_name):
        """Pobiera konfigurację kategorii po nazwie"""
        for category in self.available_categories.values():
            if category["name"] == category_name:
                return category
        return None

    def validate_category(self, category_name):
        """Sprawdza czy kategoria jest dostępna"""
        return category_name in [cat["name"] for cat in self.available_categories.values()]

    def get_category_statistics(self, category_name):
        """Zwraca statystyki dla kategorii"""
        if not self.validate_category(category_name):
            return None
            
        # Tutaj można dodać logikę pobierania statystyk z bazy danych
        # Na razie zwracamy przykładowe dane
        stats = {
            "stroj_dwuczesciowy": {
                "total_products": 150,
                "mapped_products": 120,
                "unmapped_products": 30,
                "success_rate": 0.85
            },
            "stroj_jednoczesciowy": {
                "total_products": 80,
                "mapped_products": 65,
                "unmapped_products": 15,
                "success_rate": 0.82
            }
        }
        
        return stats.get(category_name, {})

    def show_category_info(self, category_name):
        """Wyświetla informacje o kategorii"""
        category = self.get_category_by_name(category_name)
        if not category:
            print(f"❌ Nieznana kategoria: {category_name}")
            return
            
        stats = self.get_category_statistics(category_name)
        
        print(f"\n📊 === INFORMACJE O KATEGORII: {category['display_name']} ===\n")
        print(f"📝 Opis: {category['description']}")
        
        if stats:
            print(f"📦 Łącznie produktów: {stats['total_products']}")
            print(f"✅ Zmapowane: {stats['mapped_products']}")
            print(f"⏳ Do mapowania: {stats['unmapped_products']}")
            print(f"📈 Skuteczność: {stats['success_rate']*100:.1f}%")
        
        # Pokaż dostępne modele dla tej kategorii
        print(f"\n🎨 Dostępne modele:")
        for model_name, characteristics in lupo_knowledge.model_characteristics.items():
            if category_name in characteristics["typical_types"] or category_name == "wszystkie":
                colors = ", ".join(characteristics["typical_colors"])
                print(f"   • {model_name}: {colors}")

    def get_processing_config(self, category_name):
        """Zwraca konfigurację przetwarzania dla kategorii"""
        category = self.get_category_by_name(category_name)
        if not category:
            return None
            
        config = {
            "category_name": category["name"],
            "display_name": category["display_name"],
            "url": category["url"],
            "batch_size": 10,  # liczba produktów do przetworzenia na raz
            "wait_between_products": 2,  # sekundy między produktami
            "max_retries": 3,
            "use_learning": True,
            "validate_consistency": True
        }
        
        # Specjalne ustawienia dla różnych kategorii
        if category_name == "stroj_jednoczesciowy":
            config["additional_attributes"] = [25]  # wyższy stan
            config["description_patterns"] = ["stroj_jednoczesciowy", "stroj_jednoczesciowy_z_biustonoszem"]
        elif category_name == "stroj_dwuczesciowy":
            config["description_patterns"] = ["biustonosz_usztywniony", "biustonosz_miekki", "wiazany_na_szyi"]
        
        return config


# Globalna instancja menedżera kategorii
category_manager = CategoryManager()


