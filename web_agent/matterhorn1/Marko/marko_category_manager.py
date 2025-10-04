#!/usr/bin/env python3
"""
Menedżer kategorii produktów Marko
Pozwala na wybór i zarządzanie różnymi kategoriami produktów marki Marko
"""

from marko_knowledge_base import marko_knowledge


class MarkoCategoryManager:
    """Menedżer kategorii produktów marki Marko"""

    def __init__(self):
        self.available_categories = {
            "1": {
                "name": "kostium_dwuczesciowy",
                "display_name": "Kostiumy Dwuczęściowe",
                "description": "Biustonosze, figi, kostiumy dwuczęściowe - eleganckie stroje kąpielowe",
                "url": "http://localhost:8000/admin/matterhorn/products/?active=true&brand=Marko&category_name=Kostiumy+Dwuczęściowe&is_mapped__exact=0"
            },
            "2": {
                "name": "kostium_jednoczesciowy",
                "display_name": "Kostiumy Jednoczęściowe",
                "description": "Kostiumy jednoczęściowe, eleganckie one-piece",
                "url": "http://localhost:8000/admin/matterhorn/products/?active=true&brand=Marko&category_name=Kostiumy+Jednoczęściowe&is_mapped__exact=0"
            },
            "3": {
                "name": "wszystkie_kategorie",
                "display_name": "Wszystkie Kategorie Marko",
                "description": "Wszystkie produkty marki Marko",
                "url": "http://localhost:8000/admin/matterhorn/products/?active=true&brand=Marko&is_mapped__exact=0"
            }
        }

    def show_category_menu(self):
        """Wyświetla menu wyboru kategorii"""
        print("\n🎯 === WYBÓR KATEGORII PRODUKTÓW MARKO ===\n")

        for key, category in self.available_categories.items():
            print(f"{key}. {category['display_name']}")
            print(f"   📝 {category['description']}")
            print()

    def get_category_choice(self):
        """Pobiera wybór kategorii od użytkownika"""
        while True:
            try:
                choice = input("Wybierz kategorię (1-3): ").strip()

                if choice in self.available_categories:
                    selected_category = self.available_categories[choice]
                    print(f"\n✅ Wybrano: {selected_category['display_name']}")
                    print(f"📝 {selected_category['description']}")
                    return selected_category
                else:
                    print("❌ Nieprawidłowy wybór. Wybierz 1-3.")

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

        # Statystyki na podstawie embeddings jeśli dostępne
        embeddings_stats = marko_knowledge.get_learning_statistics()

        # Domyślne statystyki dla Marko
        stats = {
            "kostium_dwuczesciowy": {
                "total_products": 45,
                "mapped_products": 35,
                "unmapped_products": 10,
                "success_rate": 0.78,
                "main_models": ["Ada"]
            },
            "kostium_jednoczesciowy": {
                "total_products": 25,
                "mapped_products": 18,
                "unmapped_products": 7,
                "success_rate": 0.72,
                "main_models": ["Ada"]
            },
            "wszystkie_kategorie": {
                "total_products": 70,
                "mapped_products": 53,
                "unmapped_products": 17,
                "success_rate": 0.76,
                "main_models": ["Ada"]
            }
        }

        # Jeśli embeddings są dostępne, użyj ich statystyk
        if embeddings_stats.get("embeddings_available"):
            base_stats = stats.get(category_name, {})
            base_stats.update({
                "embeddings_products": embeddings_stats.get("total_products", 0),
                "learning_enabled": True
            })
            return base_stats

        return stats.get(category_name, {})

    def show_category_info(self, category_name):
        """Wyświetla informacje o kategorii"""
        category = self.get_category_by_name(category_name)
        if not category:
            print(f"❌ Nieznana kategoria: {category_name}")
            return

        stats = self.get_category_statistics(category_name)

        print(
            f"\n📊 === INFORMACJE O KATEGORII: {category['display_name']} ===\n")
        print(f"📝 Opis: {category['description']}")

        if stats:
            print(f"📦 Łącznie produktów: {stats['total_products']}")
            print(f"✅ Zmapowane: {stats['mapped_products']}")
            print(f"⏳ Do mapowania: {stats['unmapped_products']}")
            success_rate_percent = stats['success_rate'] * 100
            print(f"📈 Skuteczność: {success_rate_percent:.1f}%")

            if stats.get("main_models"):
                print(f"🎨 Główne modele: {', '.join(stats['main_models'])}")

            if stats.get("learning_enabled"):
                embeddings_count = stats.get('embeddings_products', 0)
                print(
                    f"🧠 Embeddings: {embeddings_count} produktów w bazie wiedzy")

        # Pokaż dostępne modele dla tej kategorii
        print("\n🎨 Dostępne modele:")
        for model_name, characteristics in marko_knowledge.model_characteristics.items():
            if category_name in characteristics["typical_types"] or category_name == "wszystkie_kategorie":
                colors = ", ".join(characteristics["typical_colors"])
                sizes = ", ".join(characteristics["common_sizes"])
                print(f"   • {model_name}: {colors} (rozmiary: {sizes})")

    def get_processing_config(self, category_name):
        """Zwraca konfigurację przetwarzania dla kategorii"""
        category = self.get_category_by_name(category_name)
        if not category:
            return None

        config = {
            "category_name": category["name"],
            "display_name": category["display_name"],
            "url": category["url"],
            # liczba produktów do przetworzenia na raz (większa niż LupoLine)
            "batch_size": 15,
            "wait_between_products": 2,  # sekundy między produktami
            "max_retries": 3,
            "use_learning": True,
            "validate_consistency": True,
            "use_embeddings": True,  # Włącz embeddings dla Marko
            "brand": "Marko"
        }

        # Specjalne ustawienia dla różnych kategorii
        if category_name == "kostium_jednoczesciowy":
            config["additional_attributes"] = [25]  # wyższy stan
            config["description_patterns"] = [
                "kostium_jednoczesciowy", "one-piece"]
        elif category_name == "kostium_dwuczesciowy":
            config["description_patterns"] = ["kostium_usztywniony",
                                              "kostium_push_up", "kostium_regulowany"]
            config["additional_attributes"] = [24]  # zapinane z tyłu

        return config

    def get_brand_specific_settings(self):
        """Zwraca ustawienia specyficzne dla marki Marko"""
        brand_characteristics = marko_knowledge.get_brand_specific_characteristics()

        return {
            "brand_name": "Marko",
            "brand_style": brand_characteristics["brand_style"],
            "target_audience": brand_characteristics["target_audience"],
            "special_features": brand_characteristics["special_features"],
            "packaging_info": brand_characteristics["packaging"],
            "sizing_advice": brand_characteristics["sizing_advice"],
            "typical_materials": marko_knowledge.typical_materials,
            "color_mapping": marko_knowledge.producer_color_mapping
        }

    def show_brand_info(self):
        """Wyświetla informacje o marce Marko"""
        settings = self.get_brand_specific_settings()

        print(f"\n🏷️ === INFORMACJE O MARCE: {settings['brand_name']} ===\n")
        print(f"🎨 Styl: {settings['brand_style']}")
        print(f"👥 Grupa docelowa: {settings['target_audience']}")
        print(f"✨ Specjalne cechy: {', '.join(settings['special_features'])}")
        print(f"📦 Opakowanie: {settings['packaging_info']}")
        print(f"📏 Porada rozmiarowa: {settings['sizing_advice']}")

        print("\n🎨 Dostępne kolory:")
        for producer_color, variants in settings['color_mapping'].items():
            print(f"   • {producer_color}: {', '.join(variants)}")

        print("\n🧵 Typowe materiały:")
        for material_type, composition in settings['typical_materials'].items():
            materials_str = ", ".join(
                [f"{c['component']} {c['percentage']}%" for c in composition])
            print(f"   • {material_type}: {materials_str}")

    def get_learning_recommendations(self):
        """Zwraca rekomendacje dotyczące uczenia się"""
        stats = marko_knowledge.get_learning_statistics()

        recommendations = []

        if not stats.get("embeddings_available"):
            recommendations.append(
                "🔧 Włącz embeddings dla lepszej klasyfikacji produktów")
            recommendations.append(
                "📚 Rozpocznij od przetworzenia 10-15 produktów dla nauki")

        if stats.get("total_products", 0) < 20:
            recommendations.append(
                "📈 Przetwórz więcej produktów dla lepszej bazy wiedzy")

        if stats.get("total_products", 0) > 50:
            recommendations.append(
                "🎯 System jest dobrze wytrenowany - można przetwarzać większe partie")

        return recommendations


# Globalna instancja menedżera kategorii
marko_category_manager = MarkoCategoryManager()
