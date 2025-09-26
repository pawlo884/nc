#!/usr/bin/env python3
"""
Przykład rozszerzonego workflow z bazą wiedzy i systemem uczenia
"""

from matterhorn.Lupo_line.lupo_line_knowledge_base import lupo_knowledge
from matterhorn.Lupo_line.agent_learning_system import learning_system


def enhanced_mpd_workflow_example():
    """Przykład jak używać bazy wiedzy w workflow MPD"""

    # Przykładowe dane produktu
    product_title = "Kostium dwuczęściowy Biustonosz Bralet Model Ember Multicolor - Lupo Line"
    product_description = """
    Biustonosz Wave to model stworzony z myślą o kobietach z pełniejszym biustem, 
    które pragną połączyć komfort z modnym, odważnym wzorem. Biustonosz posiada 
    miękkie miseczki z modelującymi cięciami oraz jest usztywniony fiszbinami, 
    dzięki czemu doskonale podtrzymuje średnie i duże biusty. Ramiączka regulowane, 
    nieodpinane.
    """

    print("🧠 === ROZSZERZONY WORKFLOW Z BAZĄ WIEDZY ===\n")

    # 1. 🎯 ANALIZA Z BAZĄ WIEDZY
    print("1️⃣ ANALIZA PRODUKTU Z BAZĄ WIEDZY:")

    # Sugestie kolorów
    color_suggestions = lupo_knowledge.get_smart_color_suggestions(
        product_title)
    print(f"   🎨 Sugestie kolorów: {color_suggestions}")

    # Analiza wzorców opisu
    enhanced_patterns = lupo_knowledge.enhance_description_analysis(
        product_description)
    print(f"   📋 Wykryte wzorce marki:")
    for pattern in enhanced_patterns:
        print(
            f"      • {pattern['pattern']}: '{pattern['keyword']}' (pewność: {pattern['confidence']})")

    # Przewidywanie atrybutów na podstawie modelu
    model_name = "Ember"  # wyciągnięte z tytułu
    predicted_attrs = lupo_knowledge.predict_attributes_by_model(model_name)
    print(f"   🤖 Model {model_name} zwykle ma atrybuty: {predicted_attrs}")

    # Sugestie materiałów
    suggested_materials = lupo_knowledge.suggest_material_composition(
        "Biustonosz", model_name)
    print(f"   🧪 Sugerowany skład materiału: {suggested_materials}")

    print()

    # 2. 🔍 STANDARDOWA ANALIZA ATRYBUTÓW
    print("2️⃣ STANDARDOWA ANALIZA ATRYBUTÓW:")
    # (tutaj byłby kod extract_mpd_attributes_from_description)
    detected_attributes = [27, 9, 15, 23, 5]  # przykład
    print(f"   ✅ Wykryte atrybuty: {detected_attributes}")

    # 3. ✅ WALIDACJA SPÓJNOŚCI
    print("3️⃣ WALIDACJA SPÓJNOŚCI:")
    validation_issues = lupo_knowledge.validate_product_consistency(
        product_title, product_description, detected_attributes
    )

    if validation_issues:
        print("   ⚠️ Znalezione problemy:")
        for issue in validation_issues:
            print(f"      • {issue['type']}: {issue['suggestion']}")
    else:
        print("   ✅ Produkt spójny z bazą wiedzy")

    print()

    # 4. 📊 LOGOWANIE UCZENIA
    print("4️⃣ LOGOWANIE PROCESU UCZENIA:")

    product_data = {
        "title": product_title,
        "model": model_name,
        "description": product_description,
        "attributes": detected_attributes,
        "producer_color": "Multicolor",
        "main_color": "wielokolorowy",
        "series_name": "strój kąpielowy Ember - Lupo Line",
        "materials": suggested_materials,
        "success": True,
        "errors": []
    }

    learning_system.log_product_processing(product_data)
    learning_system.save_knowledge_base()

    # 5. 📈 GENEROWANIE RAPORTU
    print("5️⃣ RAPORT UCZENIA:")

    model_insights = learning_system.get_model_insights(model_name)
    if model_insights:
        print(f"   📊 Insights dla {model_name}:")
        print(f"      • Próbki: {model_insights['sample_size']}")
        print(f"      • Skuteczność: {model_insights['success_rate']*100}%")
        print(
            f"      • Częste atrybuty: {model_insights['frequent_attributes']}")
        print(f"      • Częste kolory: {model_insights['frequent_colors']}")

    full_report = learning_system.generate_learning_report()
    print(
        f"   📈 Ogólna skuteczność: {full_report['summary']['success_rate']*100}%")
    print(
        f"   📦 Łącznie produktów: {full_report['summary']['total_products']}")

    print()
    print("🎉 WORKFLOW ZAKOŃCZONY POMYŚLNIE!")


if __name__ == "__main__":
    enhanced_mpd_workflow_example()
